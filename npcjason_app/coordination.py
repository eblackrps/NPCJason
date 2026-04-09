from __future__ import annotations

from dataclasses import dataclass
import time
import uuid
from typing import Optional

from .persistence import sanitize_shared_state_payload


PRESENCE_STALE_SECONDS = 35
CONVERSATION_TTL_SECONDS = 180
COMMAND_TTL_SECONDS = 30


@dataclass
class PresenceRecord:
    pet_id: str
    name: str
    skin: str
    mood: str
    x: int
    y: int
    friend_of: Optional[str]
    pid: int


class PetCoordinator:
    def __init__(self, store, pet_id, logger=None):
        self.store = store
        self.pet_id = pet_id
        self.logger = logger

    def cleanup(self, data, now=None):
        current = time.time() if now is None else float(now)
        instances = data.setdefault("instances", {})
        stale_ids = [
            pet_id
            for pet_id, info in instances.items()
            if current - info.get("updated_at", 0) > PRESENCE_STALE_SECONDS
        ]
        for stale_id in stale_ids:
            instances.pop(stale_id, None)

        data["conversations"] = [
            conversation
            for conversation in data.setdefault("conversations", [])
            if current - conversation.get("created_at", 0) <= CONVERSATION_TTL_SECONDS
        ]
        data["commands"] = [
            command
            for command in data.setdefault("commands", [])
            if current - command.get("created_at", 0) <= COMMAND_TTL_SECONDS
        ]
        return data

    def _read_state(self):
        raw_state = self.store.read()
        sanitized, warnings = sanitize_shared_state_payload(raw_state)
        for warning in warnings:
            self._log("warning", "shared-state: " + warning)
        if sanitized != raw_state and hasattr(self.store, "write"):
            self.store.write(sanitized)
        return sanitized

    def _update_state(self, mutator):
        def wrapped(data):
            sanitized, warnings = sanitize_shared_state_payload(data)
            for warning in warnings:
                self._log("warning", "shared-state: " + warning)
            data.clear()
            data.update(sanitized)
            result = mutator(data)
            sanitized, warnings = sanitize_shared_state_payload(data)
            for warning in warnings:
                self._log("warning", "shared-state: " + warning)
            data.clear()
            data.update(sanitized)
            return result

        return self.store.update(wrapped)

    def active_other_instances(self, now=None):
        current = time.time() if now is None else float(now)
        shared_state = self._read_state()
        active = []
        for pet_id, info in shared_state.get("instances", {}).items():
            if pet_id == self.pet_id:
                continue
            if current - info.get("updated_at", 0) > PRESENCE_STALE_SECONDS:
                continue
            active.append((pet_id, info))
        return active

    def publish_presence(self, record):
        def mutate(data):
            self.cleanup(data)
            data["instances"][self.pet_id] = {
                "updated_at": time.time(),
                "x": record.x,
                "y": record.y,
                "mood": record.mood,
                "skin": record.skin,
                "name": record.name,
                "friend_of": record.friend_of,
                "pid": record.pid,
            }

        self._update_state(mutate)

    def unregister_presence(self):
        def mutate(data):
            self.cleanup(data)
            data.get("instances", {}).pop(self.pet_id, None)
            data["commands"] = [
                command for command in data.get("commands", []) if command.get("target") != self.pet_id
            ]

        self._update_state(mutate)

    def enqueue_command(self, target_pet_id, action):
        def mutate(data):
            self.cleanup(data)
            data.setdefault("commands", []).append(
                {
                    "id": uuid.uuid4().hex,
                    "created_at": time.time(),
                    "target": target_pet_id,
                    "action": action,
                }
            )

        self._update_state(mutate)

    def consume_commands(self):
        executed = []
        actions = []
        shared_state = self._read_state()
        for command in shared_state.get("commands", []):
            if command.get("target") != self.pet_id:
                continue
            command_id = command.get("id")
            if command_id:
                executed.append(command_id)
            actions.append(command.get("action"))

        if executed:
            def mutate(data):
                self.cleanup(data)
                data["commands"] = [
                    command
                    for command in data.get("commands", [])
                    if command.get("id") not in executed
                ]

            self._update_state(mutate)
        return actions

    def add_conversation(self, conversation):
        def mutate(data):
            self.cleanup(data)
            data.setdefault("conversations", []).append(conversation)

        self._update_state(mutate)

    def pending_conversations(self, seen_ids, now=None):
        current = time.time() if now is None else float(now)
        shared_state = self._read_state()
        pending = []
        seen = set(seen_ids)
        for conversation in shared_state.get("conversations", []):
            conversation_id = conversation.get("id")
            if not conversation_id or conversation_id in seen:
                continue
            if current - conversation.get("created_at", 0) > CONVERSATION_TTL_SECONDS:
                continue
            if self.pet_id not in conversation.get("participants", []):
                continue
            pending.append(conversation)
        return pending

    def _log(self, level, message):
        if not self.logger:
            return
        log_method = getattr(self.logger, level, None)
        if callable(log_method):
            log_method(message)
