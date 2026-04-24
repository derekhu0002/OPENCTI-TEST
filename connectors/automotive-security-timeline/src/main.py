from __future__ import annotations

import hashlib
import os
import re
import traceback
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, List

import requests
import stix2
from bs4 import BeautifulSoup
from pycti import OpenCTIConnectorHelper


TIMELINE_NAMESPACE = uuid.UUID("9f55e2ad-2994-4583-a41b-96ee011d4c70")
SOURCE_NAME = "automotive-security-timeline"
TIMELINE_URL = "https://autosec-timeline.delikely.eu.org/static/Automotive%20Security%20Timeline.json"
USER_AGENT = "opencti-automotive-timeline-connector/1.0"
DATE_PATTERN = re.compile(r"(?P<year>\d{4})年\s*(?P<month>\d{1,2})月\s*(?P<day>\d{1,2})日")


@dataclass
class TimelineEvent:
    event_id: str
    title: str
    description: str
    published: str
    group: str
    source_url: str
    content_hash: str


class AutomotiveSecurityTimelineConnector:
    def __init__(self) -> None:
        duration_period = os.getenv("CONNECTOR_DURATION_PERIOD", "PT24H")
        self.source_url = os.getenv("AUTOMOTIVE_TIMELINE_SOURCE_URL", TIMELINE_URL)
        self.request_timeout = int(os.getenv("AUTOMOTIVE_TIMELINE_REQUEST_TIMEOUT", "60"))
        self.verify_tls = os.getenv("AUTOMOTIVE_TIMELINE_VERIFY_TLS", "true").lower() == "true"
        self.update_existing = os.getenv("AUTOMOTIVE_TIMELINE_UPDATE_EXISTING", "true").lower() == "true"

        config = {
            "opencti": {
                "url": os.environ["OPENCTI_URL"],
                "token": os.environ["OPENCTI_TOKEN"],
            },
            "connector": {
                "id": os.environ["CONNECTOR_ID"],
                "type": os.getenv("CONNECTOR_TYPE", "EXTERNAL_IMPORT"),
                "name": os.getenv("CONNECTOR_NAME", "Automotive Security Timeline"),
                "scope": os.getenv("CONNECTOR_SCOPE", "report,url"),
                "log_level": os.getenv("CONNECTOR_LOG_LEVEL", "info"),
                "duration_period": duration_period,
                "auto": False,
                "update_existing_data": self.update_existing,
            },
        }
        self.helper = OpenCTIConnectorHelper(config)
        self.author = stix2.Identity(
            id=self._stable_stix_id("identity", SOURCE_NAME),
            identity_class="organization",
            name="Automotive Security Timeline",
            description="Automotive Security Timeline project curated by the automotive-security community.",
        )

    def _stable_stix_id(self, object_type: str, value: str) -> str:
        return f"{object_type}--{uuid.uuid5(TIMELINE_NAMESPACE, value)}"

    def _parse_date(self, raw_date: str | None = None, start_date: dict | None = None) -> str:
        if start_date is not None:
            published = datetime(
                int(start_date["year"]),
                int(start_date["month"]),
                int(start_date["day"]),
                tzinfo=timezone.utc,
            )
            return published.isoformat().replace("+00:00", "Z")

        if raw_date is None:
            raise ValueError("Missing date input")

        match = DATE_PATTERN.search(raw_date)
        if not match:
            raise ValueError(f"Unsupported date format: {raw_date}")
        published = datetime(
            int(match.group("year")),
            int(match.group("month")),
            int(match.group("day")),
            tzinfo=timezone.utc,
        )
        return published.isoformat().replace("+00:00", "Z")

    def _event_hash(self, title: str, description: str, published: str, source_url: str) -> str:
        payload = "\n".join([title.strip(), description.strip(), published, source_url.strip()])
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def _extract_group(self, title: str, description: str) -> str:
        text = f"{title} {description}".lower()
        if "cve-" in text or "漏洞" in text or "溢出" in text or "idor" in text:
            return "vulnerability"
        return "event"

    def _extract_event_links(self, paragraph) -> List[str]:
        links: List[str] = []
        for anchor in paragraph.find_all("a", href=True):
            href = anchor["href"].strip()
            if href.startswith("http"):
                links.append(href)
        return links

    def _extract_source_url_from_caption(self, caption_html: str | None) -> str | None:
        if not caption_html:
            return None

        soup = BeautifulSoup(caption_html, "html.parser")
        anchor = soup.find("a", href=True)
        if anchor is None:
            return None

        href = anchor["href"].strip()
        return href if href.startswith("http") else None

    def _fetch_events_from_json(self) -> List[TimelineEvent]:
        response = requests.get(
            self.source_url,
            headers={"User-Agent": USER_AGENT},
            timeout=self.request_timeout,
            verify=self.verify_tls,
        )
        response.raise_for_status()
        payload = response.json()

        events: List[TimelineEvent] = []
        for item in payload.get("events", []):
            text = item.get("text", {})
            start_date = item.get("start_date", {})
            title = (text.get("headline") or "").strip()
            description = (text.get("text") or "").replace("<br/>", "\n").replace("<br />", "\n").strip()
            if not title or not description or not start_date:
                continue

            published = self._parse_date(start_date=start_date)
            source_url = self._extract_source_url_from_caption(item.get("media", {}).get("caption")) or self.source_url
            group = (item.get("group") or self._extract_group(title, description)).strip().lower()
            event_key = f"{published}|{title}"
            event_hash = self._event_hash(title, description, published, source_url)
            events.append(
                TimelineEvent(
                    event_id=event_key,
                    title=title,
                    description=description,
                    published=published,
                    group=group,
                    source_url=source_url,
                    content_hash=event_hash,
                )
            )

        return events

    def _fetch_events(self) -> List[TimelineEvent]:
        if self.source_url.lower().endswith(".json"):
            return self._fetch_events_from_json()

        response = requests.get(
            self.source_url,
            headers={"User-Agent": USER_AGENT},
            timeout=self.request_timeout,
            verify=self.verify_tls,
        )
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")
        events: List[TimelineEvent] = []

        for heading in soup.find_all("h2"):
            title = heading.get_text(" ", strip=True)
            if not title or title == "车联网安全事件时间轴":
                continue

            date_text = ""
            description_parts: List[str] = []
            links: List[str] = []
            for element in heading.next_elements:
                if getattr(element, "name", None) == "h2":
                    break
                if getattr(element, "name", None) == "h3" and not date_text:
                    date_text = element.get_text(" ", strip=True)
                elif getattr(element, "name", None) == "p":
                    paragraph_text = element.get_text(" ", strip=True)
                    if paragraph_text:
                        description_parts.append(paragraph_text)
                    links.extend(self._extract_event_links(element))

            if not date_text or not description_parts:
                continue

            try:
                published = self._parse_date(date_text)
            except ValueError:
                continue

            description = "\n\n".join(dict.fromkeys(description_parts))
            source_url = links[0] if links else self.source_url
            group = self._extract_group(title, description)
            event_key = f"{published}|{title}"
            event_hash = self._event_hash(title, description, published, source_url)
            events.append(
                TimelineEvent(
                    event_id=event_key,
                    title=title,
                    description=description,
                    published=published,
                    group=group,
                    source_url=source_url,
                    content_hash=event_hash,
                )
            )

        deduplicated: Dict[str, TimelineEvent] = {}
        for event in events:
            deduplicated[event.event_id] = event
        return list(deduplicated.values())

    def _build_stix_objects(self, events: List[TimelineEvent]) -> List[object]:
        objects: List[object] = [self.author]
        for event in events:
            observable = stix2.URL(value=event.source_url)
            report = stix2.Report(
                id=self._stable_stix_id("report", event.event_id),
                created_by_ref=self.author.id,
                name=event.title,
                description=event.description,
                published=event.published,
                report_types=["vulnerability-report"] if event.group == "vulnerability" else ["threat-report"],
                object_refs=[self.author.id, observable.id],
                external_references=[
                    stix2.ExternalReference(
                        source_name=SOURCE_NAME,
                        url=event.source_url,
                        description="Source entry from Automotive Security Timeline",
                    )
                ],
                allow_custom=True,
                custom_properties={
                    "x_opencti_main_observable_type": "Url",
                    "x_automotive_timeline_group": event.group,
                },
            )
            objects.extend([observable, report])
        return objects

    def process_message(self) -> str:
        now = datetime.now(timezone.utc)
        friendly_name = f"{self.helper.connect_name} run @ {now.strftime('%Y-%m-%d %H:%M:%S')}"
        work_id = self.helper.api.work.initiate_work(self.helper.connect_id, friendly_name)
        self.helper.connector_logger.info(
            "Fetching timeline entries",
            {"source_url": self.source_url, "work_id": work_id},
        )

        state = self.helper.get_state() or {}
        previous_hashes = state.get("event_hashes", {})
        current_hashes: Dict[str, str] = {}

        try:
            events = self._fetch_events()
            self.helper.connector_logger.info(
                "Timeline parsed",
                {"events_found": len(events), "work_id": work_id},
            )

            changed_events: List[TimelineEvent] = []
            for event in events:
                current_hashes[event.event_id] = event.content_hash
                if previous_hashes.get(event.event_id) != event.content_hash:
                    changed_events.append(event)

            if changed_events:
                stix_objects = self._build_stix_objects(changed_events)
                bundle = self.helper.stix2_create_bundle(stix_objects)
                bundles_sent = self.helper.send_stix2_bundle(
                    bundle,
                    update=self.update_existing,
                    work_id=work_id,
                    cleanup_inconsistent_bundle=True,
                )
                self.helper.connector_logger.info(
                    "Timeline changes sent to OpenCTI",
                    {
                        "changed_events": len(changed_events),
                        "stix_objects": len(stix_objects),
                        "bundles_sent": len(bundles_sent),
                        "work_id": work_id,
                    },
                )
                message = f"Imported or updated {len(changed_events)} timeline events"
            else:
                self.helper.connector_logger.info(
                    "No timeline changes detected",
                    {"events_found": len(events), "work_id": work_id},
                )
                message = "No new timeline changes detected"

            self.helper.set_state(
                {
                    "event_hashes": current_hashes,
                    "last_run": now.isoformat().replace("+00:00", "Z"),
                    "last_event_count": len(events),
                }
            )
            self.helper.api.work.to_processed(work_id, message)
            return message
        except Exception as exc:
            self.helper.connector_logger.error(
                "Connector execution failed",
                {"error": str(exc), "work_id": work_id},
            )
            raise

    def run(self) -> None:
        self.helper.connector_logger.info(
            "Starting connector scheduler",
            {
                "duration_period": os.getenv("CONNECTOR_DURATION_PERIOD", "PT24H"),
                "source_url": self.source_url,
            },
        )
        self.helper.schedule_iso(
            message_callback=self.process_message,
            duration_period=os.getenv("CONNECTOR_DURATION_PERIOD", "PT24H"),
        )


if __name__ == "__main__":
    try:
        AutomotiveSecurityTimelineConnector().run()
    except BaseException:
        traceback.print_exc()
        raise