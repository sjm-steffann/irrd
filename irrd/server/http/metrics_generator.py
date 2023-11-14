import datetime
import logging
import os
import textwrap
import time
from typing import Any, Dict, Iterable

from irrd import __version__, ENV_MAIN_STARTUP_TIME
from irrd.storage.database_handler import DatabaseHandler
from irrd.storage.queries import DatabaseStatusQuery, RPSLDatabaseObjectStatisticsQuery

logger = logging.getLogger(__name__)


class MetricsGenerator:

    def generate_metrics(self) -> str:
        """
        Generate a machine-readable overview of database status.
        """
        database_handler = DatabaseHandler()

        statistics_query = RPSLDatabaseObjectStatisticsQuery()
        statistics_results = list(database_handler.execute_query(statistics_query))
        status_query = DatabaseStatusQuery()
        status_results = list(database_handler.execute_query(status_query))

        statistics = sorted(statistics_results, key=lambda item: f"{item['source']}-{item['object_class']}")
        status = sorted(status_results, key=lambda item: item['source'])

        results = [
            self._generate_header(),
            self._generate_object_counts(statistics),
            self._generate_updated(status),
            self._generate_last_error(status),
            self._generate_serial_newest_mirror(status),
            self._generate_serial_last_export(status),
            self._generate_serial_oldest_journal(status),
            self._generate_serial_newest_journal(status),
        ]
        database_handler.close()
        return '\n'.join(results) + '\n'

    def _generate_header(self) -> str:
        """
        Generate the header of the report, containing basic info like version and uptime
        """
        return textwrap.dedent(f"""
        # HELP irrd_info Info from IRRD, value is always 1
        # TYPE irrd_info gauge
        irrd_info{{version="{__version__}"}} 1
        
        # HELP irrd_uptime_seconds Uptime of IRRD in seconds
        # TYPE irrd_uptime_seconds gauge
        irrd_uptime_seconds {int(time.time()) - int(os.environ[ENV_MAIN_STARTUP_TIME])}
        
        # HELP irrd_startup_timestamp Startup time of IRRD in seconds since UNIX epoch
        # TYPE irrd_startup_timestamp gauge
        irrd_startup_timestamp {os.environ[ENV_MAIN_STARTUP_TIME]}
        """).strip() + '\n'

    def _generate_object_counts(self, statistics: Iterable[Dict[str, Any]]) -> str:
        """
        Generate statistics about the number of object types per source
        """
        lines = []
        for stat in statistics:
            lines.append(
                f"""irrd_object_class{{source="{stat['source']}", object_class="{stat['object_class']}"}} """
                f"""{stat['count']}"""
            )

        return textwrap.dedent("""
        # HELP irrd_object_class Number of objects per class per source
        # TYPE irrd_object_class gauge
        """).lstrip() + '\n'.join(lines) + '\n'

    def _generate_updated(self, status: Iterable[Dict[str, Any]]) -> str:
        """
        Generate statistics about the time since last update
        """
        now = datetime.datetime.now(tz=datetime.timezone.utc)
        lines = []
        for stat in status:
            if 'updated' not in stat or stat['updated'] is None:
                continue
            diff = now - stat['updated']
            lines.append(f"""irrd_seconds_since_last_update{{source="{stat['source']}"}} {diff.total_seconds()}""")

        return textwrap.dedent("""
        # HELP irrd_seconds_since_last_update Seconds since the last update
        # TYPE irrd_seconds_since_last_update gauge
        """).lstrip() + '\n'.join(lines) + '\n'

    def _generate_last_error(self, status: Iterable[Dict[str, Any]]) -> str:
        """
        Generate statistics about the time since last update
        """
        now = datetime.datetime.now(tz=datetime.timezone.utc)
        lines = []
        for stat in status:
            if 'last_error_timestamp' in stat and stat['last_error_timestamp'] is not None:
                diff = now - stat['last_error_timestamp']
                lines.append(f"""irrd_seconds_since_last_error{{source="{stat['source']}"}} {diff.total_seconds()}""")
            else:
                # No error, so the error was infinitely long ago, right?
                lines.append(f"""irrd_seconds_since_last_error{{source="{stat['source']}"}} +Inf""")

        return textwrap.dedent("""
        # HELP irrd_seconds_since_last_error Seconds since the last error
        # TYPE irrd_seconds_since_last_error gauge
        """).lstrip() + '\n'.join(lines) + '\n'

    def _generate_serial_newest_mirror(self, status: Iterable[Dict[str, Any]]) -> str:
        """
        Generate statistics about the newest mirrored serial
        """
        lines = []
        for stat in status:
            if 'serial_newest_mirror' not in stat or stat['serial_newest_mirror'] is None:
                continue
            lines.append(f"""irrd_serial_newest_mirror{{source="{stat['source']}"}} {stat['serial_newest_mirror']}""")

        return textwrap.dedent("""
        # HELP irrd_serial_newest_mirror Newest serial number mirrored from upstream
        # TYPE irrd_serial_newest_mirror gauge
        """).lstrip() + '\n'.join(lines) + '\n'

    def _generate_serial_last_export(self, status: Iterable[Dict[str, Any]]) -> str:
        """
        Generate statistics about the last export
        """
        lines = []
        for stat in status:
            if 'serial_last_export' not in stat or stat['serial_last_export'] is None:
                continue
            lines.append(f"""irrd_serial_last_export{{source="{stat['source']}"}} {stat['serial_last_export']}""")

        return textwrap.dedent("""
        # HELP irrd_serial_last_export Last serial number exported
        # TYPE irrd_serial_last_export gauge
        """).lstrip() + '\n'.join(lines) + '\n'

    def _generate_serial_oldest_journal(self, status: Iterable[Dict[str, Any]]) -> str:
        """
        Generate statistics about the oldest serial in the journal
        """
        lines = []
        for stat in status:
            if 'serial_oldest_journal' not in stat or stat['serial_oldest_journal'] is None:
                continue
            lines.append(f"""irrd_serial_oldest_journal{{source="{stat['source']}"}} {stat['serial_oldest_journal']}""")

        return textwrap.dedent("""
        # HELP irrd_serial_oldest_journal Oldest serial in the journal
        # TYPE irrd_serial_oldest_journal gauge
        """).lstrip() + '\n'.join(lines) + '\n'

    def _generate_serial_newest_journal(self, status: Iterable[Dict[str, Any]]) -> str:
        """
        Generate statistics about the last serial in the journal
        """
        lines = []
        for stat in status:
            if 'serial_newest_journal' not in stat or stat['serial_newest_journal'] is None:
                continue
            lines.append(f"""irrd_serial_newest_journal{{source="{stat['source']}"}} {stat['serial_newest_journal']}""")

        return textwrap.dedent("""
        # HELP irrd_serial_newest_journal Newest serial in the journal
        # TYPE irrd_serial_newest_journal gauge
        """).lstrip() + '\n'.join(lines) + '\n'
