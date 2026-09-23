"""Extract Xiaohongshu group topics from an existing chat export."""

from __future__ import annotations

import csv
import json
import os
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

from .private_paths import ensure_private_dir


TOPIC_KEYS = {
    "topicId",
    "groupTopicId",
    "topicName",
    "topicIntro",
    "topicType",
    "topicIcon",
    "topicDarkIcon",
    "topicDeeplink",
    "sourceTag",
}


def parse_json_layers(value, max_layers: int = 3):
    for _ in range(max_layers):
        if not isinstance(value, str):
            break
        stripped = value.strip()
        if not stripped.startswith(("{", "[")):
            break
        try:
            value = json.loads(stripped)
        except json.JSONDecodeError:
            break
    return value


def iter_topic_payloads(value, depth: int = 0) -> Iterable[dict]:
    if depth > 8:
        return
    value = parse_json_layers(value)
    if isinstance(value, list):
        for item in value:
            yield from iter_topic_payloads(item, depth + 1)
    elif isinstance(value, dict):
        if ("topicId" in value or "groupTopicId" in value) and TOPIC_KEYS.intersection(value):
            yield value
        for nested in value.values():
            yield from iter_topic_payloads(nested, depth + 1)


def topic_key(payload: dict) -> Optional[str]:
    value = payload.get("topicId") or payload.get("groupTopicId")
    return str(value) if value not in (None, "") else None


def message_key(message: dict, index: int) -> str:
    for field in ("store_id", "uuid", "id"):
        if message.get(field) not in (None, ""):
            return f"{field}:{message[field]}"
    return f"index:{index}"


def message_identity_keys(message: dict) -> set[str]:
    """Return stable identifiers that can link a ref_message to its source card."""
    if not isinstance(message, dict):
        return set()
    return {
        f"{field}:{message[field]}"
        for field in ("store_id", "uuid", "id")
        if message.get(field) not in (None, "")
    }


def created_at_ms(message: dict) -> Optional[int]:
    try:
        value = int(message.get("created_at"))
    except (TypeError, ValueError):
        return None
    return value if value > 10**11 else value * 1000


def iso_time(value: Optional[int], offset_hours: int = 8) -> Optional[str]:
    if value is None:
        return None
    zone = timezone(timedelta(hours=offset_hours))
    return datetime.fromtimestamp(value / 1000, tz=timezone.utc).astimezone(zone).isoformat(timespec="milliseconds")


def safe_filename(value: str) -> str:
    name = re.sub(r"[^0-9A-Za-z._-]+", "_", value).strip("._-")
    return (name[:120] or "topic") + ".json"


def _new_topic(key: str) -> dict:
    return {
        "topic_id": key,
        "group_topic_id": None,
        "topic_names": [],
        "topic_intro": None,
        "topic_type": None,
        "topic_icon": None,
        "topic_dark_icon": None,
        "topic_deeplink": None,
        "source_tag": None,
        "topic_cards": {},
        "reference_messages": {},
        "related_messages": {},
    }


def _merge_metadata(topic: dict, payload: dict) -> None:
    mapping = {
        "groupTopicId": "group_topic_id",
        "topicIntro": "topic_intro",
        "topicType": "topic_type",
        "topicIcon": "topic_icon",
        "topicDarkIcon": "topic_dark_icon",
        "topicDeeplink": "topic_deeplink",
        "sourceTag": "source_tag",
    }
    for source, target in mapping.items():
        if payload.get(source) not in (None, ""):
            topic[target] = payload[source]
    name = payload.get("topicName")
    if name not in (None, "") and name not in topic["topic_names"]:
        topic["topic_names"].append(name)


def _sort_key(message: dict) -> tuple[int, int]:
    try:
        store_id = int(message.get("store_id") or 0)
    except (TypeError, ValueError):
        store_id = 0
    return created_at_ms(message) or 0, store_id


def _is_member_topic_post(payload: dict) -> bool:
    """Topic definition cards have no postId; member submissions do."""
    return payload.get("postId") not in (None, "")


def _topic_post_record(
    topic_id: str,
    topic_name: Optional[str],
    message: dict,
    payload: dict,
    direct_replies: List[dict],
) -> dict:
    return {
        "topic_id": topic_id,
        "topic_name": topic_name,
        "topic_post_id": str(payload.get("postId")),
        "message_id": message.get("id"),
        "message_uuid": message.get("uuid"),
        "store_id": message.get("store_id"),
        "sender_id": message.get("sender_id"),
        "creator": payload.get("creator"),
        "content": payload.get("content"),
        "image_list": payload.get("imageList") or [],
        "file_list": payload.get("fileList") or [],
        "note_list": payload.get("noteList") or [],
        "link": payload.get("link"),
        "created_at_asia_shanghai": iso_time(created_at_ms(message)),
        "direct_reply_count": len(direct_replies),
        "is_directly_replied": bool(direct_replies),
        "direct_reply_store_ids": [row.get("store_id") for row in direct_replies],
    }


def extract_group_topics(export: dict) -> dict:
    messages = export.get("messages")
    if not isinstance(messages, list):
        raise ValueError("messages.json must contain a messages array")
    topics: Dict[str, dict] = {}

    for index, message in enumerate(messages):
        key = message_key(message, index)
        main_payloads = {}
        reference_payloads = {}
        for payload in iter_topic_payloads(message.get("content")):
            identifier = topic_key(payload)
            if identifier:
                main_payloads[identifier] = payload
                topic = topics.setdefault(identifier, _new_topic(identifier))
                _merge_metadata(topic, payload)
        for payload in iter_topic_payloads(message.get("ref_message")):
            identifier = topic_key(payload)
            if identifier:
                reference_payloads[identifier] = payload
                topic = topics.setdefault(identifier, _new_topic(identifier))
                _merge_metadata(topic, payload)

        for identifier, payload in main_payloads.items():
            topics[identifier]["topic_cards"][key] = {
                "message": message,
                "payload": payload,
                "identities": message_identity_keys(message),
            }
        for identifier in reference_payloads:
            topics[identifier]["reference_messages"][key] = {
                "message": message,
                "target_identities": message_identity_keys(message.get("ref_message")),
            }
        for identifier in set(main_payloads) | set(reference_payloads):
            topics[identifier]["related_messages"][key] = message

    output_topics = []
    topic_messages: Dict[str, List[dict]] = {}
    topic_posts: List[dict] = []
    unreplied_topic_posts: Dict[str, List[dict]] = {}
    for identifier, topic in topics.items():
        related = list(topic["related_messages"].values())
        related.sort(key=_sort_key)
        times = [value for value in (created_at_ms(row) for row in related) if value is not None]
        store_ids = []
        for row in related:
            try:
                store_ids.append(int(row.get("store_id")))
            except (TypeError, ValueError):
                pass
        filename = safe_filename(identifier)
        topic_name = topic["topic_names"][-1] if topic["topic_names"] else None
        posts = []
        for card in topic["topic_cards"].values():
            if not _is_member_topic_post(card["payload"]):
                continue
            direct_replies = [
                reply["message"]
                for reply in topic["reference_messages"].values()
                if card["identities"].intersection(reply["target_identities"])
            ]
            direct_replies.sort(key=_sort_key)
            posts.append(
                _topic_post_record(identifier, topic_name, card["message"], card["payload"], direct_replies)
            )
        posts.sort(key=lambda row: (row["created_at_asia_shanghai"] or "", int(row.get("store_id") or 0)))
        unresponded_posts = [row for row in posts if not row["is_directly_replied"]]
        replied_post_count = len(posts) - len(unresponded_posts)
        reference_count = len(topic["reference_messages"])
        metadata = {
            "topic_id": identifier,
            "group_topic_id": topic["group_topic_id"],
            "topic_name": topic_name,
            "topic_names": topic["topic_names"],
            "topic_intro": topic["topic_intro"],
            "topic_type": topic["topic_type"],
            "topic_icon": topic["topic_icon"],
            "topic_dark_icon": topic["topic_dark_icon"],
            "topic_deeplink": topic["topic_deeplink"],
            "source_tag": topic["source_tag"],
            "topic_card_count": len(topic["topic_cards"]),
            "topic_post_count": len(posts),
            "replied_topic_post_count": replied_post_count,
            "unreplied_topic_post_count": len(unresponded_posts),
            "direct_reply_count": reference_count,
            "related_message_count": len(related),
            "first_seen_at_asia_shanghai": iso_time(min(times) if times else None),
            "last_seen_at_asia_shanghai": iso_time(max(times) if times else None),
            "first_store_id": min(store_ids) if store_ids else None,
            "last_store_id": max(store_ids) if store_ids else None,
            "topic_messages_file": f"topic_messages/{filename}",
            "unreplied_topic_posts_file": f"unreplied_topic_posts/{filename}",
        }
        output_topics.append(metadata)
        topic_messages[filename] = related
        topic_posts.extend(posts)
        unreplied_topic_posts[filename] = unresponded_posts

    output_topics.sort(key=lambda row: (row["first_store_id"] is None, row["first_store_id"] or 0, row["topic_id"]))
    topic_posts.sort(key=lambda row: (row["created_at_asia_shanghai"] or "", int(row.get("store_id") or 0)))
    return {
        "group_id": export.get("group_id"),
        "source_message_count": len(messages),
        "topic_count": len(output_topics),
        "topic_card_count": sum(row["topic_card_count"] for row in output_topics),
        "topic_post_count": sum(row["topic_post_count"] for row in output_topics),
        "replied_topic_post_count": sum(row["replied_topic_post_count"] for row in output_topics),
        "unreplied_topic_post_count": sum(row["unreplied_topic_post_count"] for row in output_topics),
        "direct_reply_count": sum(row["direct_reply_count"] for row in output_topics),
        "related_message_count": sum(row["related_message_count"] for row in output_topics),
        "topics": output_topics,
        "_topic_messages": topic_messages,
        "_topic_posts": topic_posts,
        "_unreplied_topic_posts": unreplied_topic_posts,
    }


def _write_private(path: Path, text: str, overwrite: bool) -> None:
    if path.exists() and not overwrite:
        raise FileExistsError(f"refusing to overwrite existing file: {path}")
    ensure_private_dir(path.parent)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8", newline="") as handle:
        handle.write(text)
    path.chmod(0o600)


def write_topic_export(
    messages_json: Path,
    output_dir: Path,
    overwrite: bool = False,
    unreplied_posts_only: bool = False,
) -> Tuple[dict, dict]:
    messages_json = Path(messages_json).expanduser().resolve()
    output_dir = Path(output_dir).expanduser().resolve()
    export = json.loads(messages_json.read_text(encoding="utf-8"))
    result = extract_group_topics(export)
    per_topic = result.pop("_topic_messages")
    posts = result.pop("_topic_posts")
    per_topic_unreplied = result.pop("_unreplied_topic_posts")
    result["topic_post_filter"] = "unreplied" if unreplied_posts_only else "all"
    result["total_topic_count"] = result["topic_count"]
    result["total_topic_post_count"] = result["topic_post_count"]
    if unreplied_posts_only:
        posts = [row for row in posts if not row["is_directly_replied"]]
        selected_topic_ids = {row["topic_id"] for row in posts}
        selected_topics = [row for row in result["topics"] if row["topic_id"] in selected_topic_ids]
        selected_files = {Path(row["topic_messages_file"]).name for row in selected_topics}
        result["topics"] = selected_topics
        result["topic_count"] = len(selected_topics)
        per_topic = {name: rows for name, rows in per_topic.items() if name in selected_files}
        per_topic_unreplied = {
            name: rows for name, rows in per_topic_unreplied.items() if name in selected_files
        }
    result["selected_topic_post_count"] = len(posts)
    ensure_private_dir(output_dir)

    json_path = output_dir / "topics.json"
    csv_path = output_dir / "topics.csv"
    _write_private(json_path, json.dumps(result, ensure_ascii=False, indent=2) + "\n", overwrite)

    columns = [
        "topic_id", "group_topic_id", "topic_name", "topic_intro", "topic_type",
        "topic_card_count", "topic_post_count", "replied_topic_post_count",
        "unreplied_topic_post_count", "direct_reply_count", "related_message_count",
        "first_seen_at_asia_shanghai", "last_seen_at_asia_shanghai",
        "first_store_id", "last_store_id", "topic_deeplink", "topic_icon",
        "topic_dark_icon", "source_tag", "topic_messages_file", "unreplied_topic_posts_file",
    ]
    rows = []
    for topic in result["topics"]:
        rows.append({column: topic.get(column) for column in columns})
    from io import StringIO

    buffer = StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=columns)
    writer.writeheader()
    writer.writerows(rows)
    _write_private(csv_path, buffer.getvalue(), overwrite)

    posts_json_path = output_dir / "topic_posts.json"
    posts_csv_path = output_dir / "topic_posts.csv"
    _write_private(
        posts_json_path,
        json.dumps({"topic_post_filter": result["topic_post_filter"], "posts": posts}, ensure_ascii=False, indent=2) + "\n",
        overwrite,
    )
    post_columns = [
        "topic_id", "topic_name", "topic_post_id", "message_id", "message_uuid", "store_id",
        "sender_id", "creator", "content", "image_list", "file_list", "note_list", "link",
        "created_at_asia_shanghai", "direct_reply_count", "is_directly_replied",
        "direct_reply_store_ids",
    ]
    post_buffer = StringIO(newline="")
    post_writer = csv.DictWriter(post_buffer, fieldnames=post_columns)
    post_writer.writeheader()
    for post in posts:
        row = dict(post)
        for field in ("creator", "image_list", "file_list", "note_list", "direct_reply_store_ids"):
            row[field] = json.dumps(row.get(field), ensure_ascii=False, separators=(",", ":"))
        post_writer.writerow({column: row.get(column) for column in post_columns})
    _write_private(posts_csv_path, post_buffer.getvalue(), overwrite)

    topic_dir = output_dir / "topic_messages"
    ensure_private_dir(topic_dir)
    metadata_by_file = {Path(row["topic_messages_file"]).name: row for row in result["topics"]}
    topic_paths = []
    for filename, messages in per_topic.items():
        path = topic_dir / filename
        payload = {"topic": metadata_by_file[filename], "messages": messages}
        _write_private(path, json.dumps(payload, ensure_ascii=False, indent=2) + "\n", overwrite)
        topic_paths.append(str(path))

    unreplied_dir = output_dir / "unreplied_topic_posts"
    ensure_private_dir(unreplied_dir)
    unreplied_paths = []
    for filename, messages in per_topic_unreplied.items():
        path = unreplied_dir / filename
        payload = {"topic": metadata_by_file[filename], "posts": messages}
        _write_private(path, json.dumps(payload, ensure_ascii=False, indent=2) + "\n", overwrite)
        unreplied_paths.append(str(path))

    paths = {
        "json": str(json_path),
        "csv": str(csv_path),
        "topic_posts_json": str(posts_json_path),
        "topic_posts_csv": str(posts_csv_path),
        "topic_messages": topic_paths,
        "unreplied_topic_posts": unreplied_paths,
    }
    return result, paths
