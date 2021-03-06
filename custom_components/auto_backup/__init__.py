"""Component to create and remove Hass.io snapshots."""
import asyncio
import logging
import os
from datetime import datetime, timedelta, timezone
from os.path import join, isfile
from typing import List

import aiohttp
import async_timeout
import homeassistant.helpers.config_validation as cv
import voluptuous as vol
from aiohttp import ClientSession
from homeassistant.components.hassio import (
    SERVICE_SNAPSHOT_FULL,
    SERVICE_SNAPSHOT_PARTIAL,
    SCHEMA_SNAPSHOT_FULL,
    SCHEMA_SNAPSHOT_PARTIAL,
    ATTR_FOLDERS,
    ATTR_ADDONS,
    ATTR_PASSWORD,
)
from homeassistant.components.hassio.const import X_HASSIO
from homeassistant.components.hassio.handler import HassioAPIError
from homeassistant.config_entries import ConfigEntry, SOURCE_IMPORT
from homeassistant.const import ATTR_NAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers.json import JSONEncoder
from homeassistant.helpers.storage import Store
from homeassistant.helpers.typing import ConfigType, HomeAssistantType, ServiceCallType
from homeassistant.util import dt as dt_util
from slugify import slugify

from .const import (
    DOMAIN,
    EVENT_SNAPSHOT_FAILED,
    EVENT_SNAPSHOTS_PURGED,
    EVENT_SNAPSHOT_SUCCESSFUL,
    EVENT_SNAPSHOT_START,
    UNSUB_LISTENER,
    DATA_AUTO_BACKUP,
    DEFAULT_BACKUP_TIMEOUT_SECONDS,
    CONF_AUTO_PURGE,
    CONF_BACKUP_TIMEOUT,
    DEFAULT_BACKUP_TIMEOUT,
)

_LOGGER = logging.getLogger(__name__)

STORAGE_KEY = "snapshots_expiry"
STORAGE_VERSION = 1

ATTR_KEEP_DAYS = "keep_days"
ATTR_EXCLUDE = "exclude"
ATTR_BACKUP_PATH = "backup_path"

DEFAULT_SNAPSHOT_FOLDERS = {
    "ssl": "ssl",
    "share": "share",
    "local add-ons": "addons/local",
    "home assistant configuration": "homeassistant",
}

CHUNK_SIZE = 64 * 1024  # 64 KB

SERVICE_PURGE = "purge"

CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: {
            vol.Optional(CONF_AUTO_PURGE, default=True): cv.boolean,
            vol.Optional(
                CONF_BACKUP_TIMEOUT, default=DEFAULT_BACKUP_TIMEOUT_SECONDS
            ): vol.Coerce(int),
        }
    },
    extra=vol.ALLOW_EXTRA,
)

SCHEMA_SNAPSHOT_FULL = SCHEMA_SNAPSHOT_FULL.extend(
    {
        vol.Optional(ATTR_KEEP_DAYS): vol.Coerce(float),
        vol.Optional(ATTR_EXCLUDE): {
            vol.Optional(ATTR_FOLDERS, default=[]): vol.All(
                cv.ensure_list, [cv.string]
            ),
            vol.Optional(ATTR_ADDONS, default=[]): vol.All(cv.ensure_list, [cv.string]),
        },
        vol.Optional(ATTR_BACKUP_PATH): cv.isdir,
    }
)

SCHEMA_SNAPSHOT_PARTIAL = SCHEMA_SNAPSHOT_PARTIAL.extend(
    {
        vol.Optional(ATTR_KEEP_DAYS): vol.Coerce(float),
        vol.Optional(ATTR_BACKUP_PATH): cv.isdir,
    }
)

COMMAND_SNAPSHOT_FULL = "/snapshots/new/full"
COMMAND_SNAPSHOT_PARTIAL = "/snapshots/new/partial"
COMMAND_SNAPSHOT_REMOVE = "/snapshots/{slug}/remove"
COMMAND_SNAPSHOT_DOWNLOAD = "/snapshots/{slug}/download"
COMMAND_GET_ADDONS = "/addons"

PLATFORMS = ["sensor"]


async def async_setup(hass: HomeAssistantType, config: ConfigType):
    """Setup the Auto Backup component."""
    hass.data.setdefault(DOMAIN, {})
    if DOMAIN in config:
        hass.async_create_task(
            hass.config_entries.flow.async_init(
                DOMAIN,
                context={"source": SOURCE_IMPORT},
                data=config[DOMAIN],
            )
        )
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Set up Auto Backup from a config entry."""
    _LOGGER.info("Setting up Auto Backup config entry %s", entry.entry_id)

    # Check local setup
    for env in ("HASSIO", "HASSIO_TOKEN"):
        if os.environ.get(env):
            continue
        _LOGGER.error(
            "Missing %s environment variable. Please check you have Hass.io installed!",
            env,
        )
        return False

    web_session = hass.helpers.aiohttp_client.async_get_clientsession()

    options = entry.data or entry.options

    # initialise AutoBackup class.
    auto_backup = hass.data[DOMAIN][DATA_AUTO_BACKUP] = AutoBackup(
        hass,
        web_session,
        options.get(CONF_AUTO_PURGE, True),
        options.get(CONF_BACKUP_TIMEOUT, DEFAULT_BACKUP_TIMEOUT),
    )

    await auto_backup.load_snapshots_expiry()

    hass.data[DOMAIN][UNSUB_LISTENER] = entry.add_update_listener(
        auto_backup.update_listener
    )

    # register services.
    async def snapshot_service_handler(call: ServiceCallType):
        """Handle Snapshot Creation Service Calls."""
        hass.async_create_task(
            auto_backup.new_snapshot(
                call.data.copy(), call.service == SERVICE_SNAPSHOT_FULL
            )
        )

    async def purge_service_handler(_):
        """Handle Snapshot Purge Service Calls."""
        await auto_backup.purge_snapshots()

    hass.services.async_register(
        DOMAIN,
        SERVICE_SNAPSHOT_FULL,
        snapshot_service_handler,
        schema=SCHEMA_SNAPSHOT_FULL,
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_SNAPSHOT_PARTIAL,
        snapshot_service_handler,
        schema=SCHEMA_SNAPSHOT_PARTIAL,
    )

    hass.services.async_register(DOMAIN, SERVICE_PURGE, purge_service_handler)

    # load the auto backup sensor.
    for component in PLATFORMS:
        hass.async_create_task(
            hass.config_entries.async_forward_entry_setup(entry, component)
        )

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Unload a config entry."""
    unload_ok = all(
        await asyncio.gather(
            *[
                hass.config_entries.async_forward_entry_unload(entry, component)
                for component in PLATFORMS
            ]
        )
    )

    hass.data[DOMAIN][UNSUB_LISTENER]()

    for service in [SERVICE_SNAPSHOT_FULL, SERVICE_SNAPSHOT_PARTIAL, SERVICE_PURGE]:
        hass.services.async_remove(DOMAIN, service)

    return unload_ok


class AutoBackup:
    def __init__(
        self,
        hass: HomeAssistantType,
        web_session: ClientSession,
        auto_purge: bool,
        backup_timeout: int,
    ):
        self._hass = hass
        self._web_session = web_session
        self._ip = os.environ["HASSIO"]
        self._auto_purge = auto_purge
        self._backup_timeout = backup_timeout * 60

        self._state = 0

        self._snapshots_store = Store(
            hass, STORAGE_VERSION, f"{DOMAIN}.{STORAGE_KEY}", encoder=JSONEncoder
        )
        self._snapshots_expiry = {}

    async def update_listener(self, hass, entry: ConfigEntry):
        """Handle options update."""
        self._auto_purge = entry.options[CONF_AUTO_PURGE]
        self._backup_timeout = entry.options[CONF_BACKUP_TIMEOUT] * 60

    async def load_snapshots_expiry(self):
        """Load snapshots expiry dates from home assistants storage."""
        data = await self._snapshots_store.async_load()

        if data is not None:
            for slug, expiry in data.items():
                self._snapshots_expiry[slug] = datetime.fromisoformat(expiry)

    async def get_addons(self, only_installed=True):
        """Retrieve a list of addons from Hass.io."""
        try:
            result = await self.send_command(COMMAND_GET_ADDONS, method="get")

            addons = result.get("data", {}).get("addons")
            if addons is None:
                raise HassioAPIError("No addons were returned.")

            if only_installed:
                return [addon for addon in addons if addon["installed"]]
            return addons

        except HassioAPIError as err:
            _LOGGER.error("Failed to retrieve addons: %s", err)

        return None

    @property
    def monitored(self):
        return len(self._snapshots_expiry)

    @property
    def purgeable(self):
        return len(self.get_purgeable_snapshots())

    @property
    def state(self):
        return self._state

    async def _replace_addon_names(self, snapshot_addons, addons=None):
        """Replace addon names with their appropriate slugs."""
        if not addons:
            addons = await self.get_addons()
        if addons:
            for addon in addons:
                for idx, snapshot_addon in enumerate(snapshot_addons):
                    # perform case insensitive match.
                    if snapshot_addon.casefold() == addon["name"].casefold():
                        snapshot_addons[idx] = addon["slug"]
        return snapshot_addons

    @staticmethod
    def _replace_folder_names(snapshot_folders):
        """Convert folder name to lower case and replace friendly folder names."""
        for idx, snapshot_folder in enumerate(snapshot_folders):
            snapshot_folder = snapshot_folder.lower()
            snapshot_folders[idx] = DEFAULT_SNAPSHOT_FOLDERS.get(
                snapshot_folder, snapshot_folder
            )

        return snapshot_folders

    async def new_snapshot(self, data, full=False):
        """Create a new snapshot in Hass.io."""
        if ATTR_NAME not in data:
            # provide a default name if none was supplied.
            time_zone = self._hass.config.time_zone
            if isinstance(time_zone, str):
                time_zone = dt_util.get_time_zone(time_zone)
            data[ATTR_NAME] = datetime.now(time_zone).strftime("%A, %b %d, %Y")

        _LOGGER.debug("Creating snapshot %s", data[ATTR_NAME])

        command = COMMAND_SNAPSHOT_FULL if full else COMMAND_SNAPSHOT_PARTIAL
        keep_days = data.pop(ATTR_KEEP_DAYS, None)
        backup_path = data.pop(ATTR_BACKUP_PATH, None)

        if full:
            # performing full backup.
            exclude = data.pop(ATTR_EXCLUDE, None)
            if exclude:
                # handle exclude config.
                command = COMMAND_SNAPSHOT_PARTIAL

                # append addons.
                addons = await self.get_addons()
                if addons:
                    excluded_addons = await self._replace_addon_names(
                        exclude[ATTR_ADDONS], addons
                    )

                    data[ATTR_ADDONS] = [
                        addon["slug"]
                        for addon in addons
                        if addon["slug"] not in excluded_addons
                    ]

                # append folders.
                excluded_folders = self._replace_folder_names(exclude[ATTR_FOLDERS])
                data[ATTR_FOLDERS] = [
                    folder
                    for folder in DEFAULT_SNAPSHOT_FOLDERS.values()
                    if folder not in excluded_folders
                ]

        else:
            # performing partial backup.
            # replace addon names with their appropriate slugs.
            if ATTR_ADDONS in data:
                data[ATTR_ADDONS] = await self._replace_addon_names(data[ATTR_ADDONS])
            # replace friendly folder names.
            if ATTR_FOLDERS in data:
                data[ATTR_FOLDERS] = self._replace_folder_names(data[ATTR_FOLDERS])

        # ensure password is scrubbed from logs.
        password = data.get(ATTR_PASSWORD)
        if password:
            data[ATTR_PASSWORD] = "<hidden>"

        _LOGGER.debug(
            "New snapshot; command: %s, keep_days: %s, data: %s, timeout: %s seconds",
            command,
            keep_days,
            data,
            self._backup_timeout,
        )

        # re-add password if it existed.
        if password:
            data[ATTR_PASSWORD] = password
            del password  # remove from memory

        self._state += 1
        self._hass.bus.async_fire(EVENT_SNAPSHOT_START, {"name": data[ATTR_NAME]})

        # make request to create new snapshot.
        try:
            result = await self.send_command(
                command, payload=data, timeout=self._backup_timeout
            )

            _LOGGER.debug("Snapshot create result: %s" % result)

            if result.get("result") == "error":
                raise HassioAPIError(
                    result.get("message")
                    or "There may be a backup already in progress."
                )

            # the result must be ok and contain the slug
            slug = result["data"]["slug"]

            # snapshot creation was successful
            _LOGGER.info(
                "Snapshot created successfully; '%s' (%s)", data[ATTR_NAME], slug
            )
            self._state -= 1
            self._hass.bus.async_fire(
                EVENT_SNAPSHOT_SUCCESSFUL, {"name": data[ATTR_NAME], "slug": slug}
            )

            if keep_days is not None:
                # set snapshot expiry
                self._snapshots_expiry[slug] = datetime.now(timezone.utc) + timedelta(
                    days=float(keep_days)
                )
                # write snapshot expiry to storage
                await self._snapshots_store.async_save(self._snapshots_expiry)

            # copy snapshot to location if specified
            if backup_path:
                await self.copy_snapshot(data[ATTR_NAME], slug, backup_path)

        except HassioAPIError as err:
            _LOGGER.error("Error during backup. %s", err)
            self._state -= 1
            self._hass.bus.async_fire(
                EVENT_SNAPSHOT_FAILED,
                {"name": data[ATTR_NAME], "error": str(err)},
            )

        # purging old snapshots
        if self._auto_purge:
            await self.purge_snapshots()

    def get_purgeable_snapshots(self) -> List[str]:
        """Returns the slugs of purgeable snapshots."""
        now = datetime.now(timezone.utc)
        return [
            slug for slug, expires in self._snapshots_expiry.items() if expires < now
        ]

    async def purge_snapshots(self):
        """Purge expired snapshots from Hass.io."""
        snapshots_purged = []
        for slug in self.get_purgeable_snapshots():
            if await self._purge_snapshot(slug):
                snapshots_purged.append(slug)

        if len(snapshots_purged) == 1:
            _LOGGER.info("Purged 1 snapshot; %s", snapshots_purged[0])
        elif len(snapshots_purged) > 1:
            _LOGGER.info(
                "Purged %s snapshots; %s",
                len(snapshots_purged),
                tuple(snapshots_purged),
            )

        if len(snapshots_purged) > 0:
            self._hass.bus.async_fire(
                EVENT_SNAPSHOTS_PURGED, {"snapshots": snapshots_purged}
            )
        else:
            _LOGGER.debug("No snapshots required purging.")

    async def _purge_snapshot(self, slug):
        """Purge an individual snapshot from Hass.io."""
        _LOGGER.debug("Attempting to remove snapshot: %s", slug)
        command = COMMAND_SNAPSHOT_REMOVE.format(slug=slug)

        try:
            result = await self.send_command(command, timeout=300)

            if result["result"] == "error":
                _LOGGER.debug("Purge result: %s", result)
                _LOGGER.warning(
                    "Issue purging snapshot (%s), assuming it was already deleted.",
                    slug,
                )

            # remove snapshot expiry.
            del self._snapshots_expiry[slug]
            # write snapshot expiry to storage.
            await self._snapshots_store.async_save(self._snapshots_expiry)

        except HassioAPIError as err:
            _LOGGER.error("Failed to purge snapshot: %s", err)
            return False
        return True

    async def copy_snapshot(self, name, slug, backup_path):
        """Download snapshot to the specified location."""

        # ensure the name is a valid filename.
        if name:
            filename = slugify(name, lowercase=False, separator="_")
        else:
            filename = slug

        # ensure the filename is a tar file.
        if not filename.endswith(".tar"):
            filename += ".tar"

        destination = join(backup_path, filename)

        # check if file already exists
        if isfile(destination):
            destination = join(backup_path, f"{slug}.tar")

        await self.download_snapshot(slug, destination)

    async def download_snapshot(self, slug, output_path):
        """Download and save a snapshot from Hass.io."""
        command = COMMAND_SNAPSHOT_DOWNLOAD.format(slug=slug)

        try:
            with async_timeout.timeout(self._backup_timeout):
                request = await self._web_session.request(
                    "get",
                    f"http://{self._ip}{command}",
                    headers={X_HASSIO: os.environ.get("HASSIO_TOKEN", "")},
                    timeout=None,
                )

                if request.status not in (200, 400):
                    _LOGGER.error("%s return code %d.", command, request.status)
                    raise HassioAPIError()

                with open(output_path, "wb") as file:
                    while True:
                        chunk = await request.content.read(CHUNK_SIZE)
                        if not chunk:
                            break
                        file.write(chunk)

                _LOGGER.info("Downloaded snapshot '%s' to '%s'", slug, output_path)
                return

        except asyncio.TimeoutError:
            _LOGGER.error("Timeout on %s request", command)

        except aiohttp.ClientError as err:
            _LOGGER.error("Client error on %s request %s", command, err)

        except IOError:
            _LOGGER.error("Failed to download snapshot '%s' to '%s'", slug, output_path)

        raise HassioAPIError(
            "Snapshot download failed. Check the logs for more information."
        )

    async def send_command(self, command, method="post", payload=None, timeout=10):
        """Send API command to Hass.io.

        This method is a coroutine.
        """
        try:
            with async_timeout.timeout(timeout):
                request = await self._web_session.request(
                    method,
                    f"http://{self._ip}{command}",
                    json=payload,
                    headers={X_HASSIO: os.environ.get("HASSIO_TOKEN", "")},
                    timeout=None,
                )

                if request.status not in (200, 400):
                    _LOGGER.error("%s return code %d.", command, request.status)
                    raise HassioAPIError()

                answer = await request.json()
                return answer

        except asyncio.TimeoutError:
            raise HassioAPIError("Timeout on %s request" % command)

        except aiohttp.ClientError as err:
            raise HassioAPIError("Client error on %s request %s" % (command, err))

        raise HassioAPIError("Failed to call %s" % command)
