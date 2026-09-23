# Analysis workflow

Read this reference when the user asks what groups discuss, what members care about, how groups differ, or which posts were not picked up.

## Evidence boundary

For each group, establish:

- earliest and latest visible timestamps;
- total records and readable human text;
- active sender IDs;
- direct-reference replies;
- image, voice, video, sticker, revoked, and system-message counts;
- partial first/last days, launch spikes, missing media semantics, and checkpoint state.

Compare rates or topic shares only after accounting for unequal observation windows. A group with six visible days and a group with four weeks of history cannot be ranked by raw totals alone.

## Three research tables

Build these before writing prose:

1. **Topic table:** group, topic, matched messages, share of readable text, unique participants, first/last appearance, directly referencing replies.
2. **Participant table:** use `sender_id` as the stable key; keep the most frequent nickname and all observed nickname variants only as display metadata. Include text count, conversation starts after a quiet gap, direct replies written, unique sender IDs replied to, direct replies received, and evidence-based interaction roles.
3. **Event table:** original message, context time, participants, direct replies, later update, and current state.

The bundled scripts create starting tables. They do not replace contextual reading. `analysis_summary.json` reports the first and last **readable human-text** timestamps, while each `source_summary.json` reports the full raw-message range.

## Deep-read candidate events

For an important message, inspect:

- 10–30 minutes before and after;
- the speaker's later messages that day;
- the next visible day;
- direct quotes, @ mentions, and callbacks using different wording.

Classify the visible state precisely:

- **Drowned:** conversation moves on and no later public response or callback appears.
- **Delayed but caught:** a later reply clearly returns to the concern.
- **Caught but unresolved:** people respond or form a plan, but the external outcome remains unknown.

Do not infer a private response, diagnosis, resolution, or stable personality.

The event table is capped per group by default. Its `possible_later_same_sender_message` field is only a retrieval hint; it may be unrelated and must never be described as a verified update without reading the surrounding timeline.

## Interpretation

- Treat keyword categories as multi-label evidence, not mutually exclusive totals.
- Look for co-occurrence: work with money, health, family, emotion, housing, or study often reveals the real concern.
- Separate surface topics from underlying needs such as sustainable work, autonomy, belonging, recognition, safety, and manageable next steps.
- Light conversation can be functional. Food, pets, games, memes, and hobbies may lower the cost of joining or help a difficult conversation continue.
- Message volume is not importance. Identify initiators, persistent responders, practical advisers, mood shifters, organizers, and low-volume members with complete event arcs.

## Report shape

For a general multi-group request, a useful report contains:

1. one-sentence thesis;
2. data boundary and limitations;
3. cross-group topic map with transparent counting notes;
4. underlying member concerns;
5. one compact profile per group;
6. interaction mechanisms and unresolved threads;
7. optional operational implications when relevant.

Avoid member rankings and long public lists of sensitive quotes. Use short, necessary examples and preserve the difference between being answered and being solved.
