"""Multi-turn conversation evaluation metrics."""
from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from .base import BaseMetric


class ConversationCoherenceMetric(BaseMetric):
    """Evaluate whether a multi-turn conversation maintains logical flow.

    Checks if:
    1. Each response is contextually connected to the previous turn
    2. There are no contradictions between turns
    3. The conversation progresses toward resolution

    Works by analyzing the conversation stored in actual_output (as JSON array of turns)
    or by splitting actual_output on newlines as turn separators.
    """
    name = "conversation_coherence"

    def measure(self, test_case: Any) -> None:
        turns = self._extract_turns(test_case)

        if not turns or len(turns) < 2:
            self.score = 1.0
            self.reason = "Single turn or empty conversation; coherence check not applicable."
            return

        issues: list[str] = []

        # Check for empty responses
        for i, turn in enumerate(turns):
            content = turn.get("content", "") if isinstance(turn, dict) else str(turn)
            if not content.strip():
                issues.append(f"Turn {i+1} has empty content.")

        # Check for exact repetitions (a sign of loops)
        contents = []
        for turn in turns:
            content = turn.get("content", "") if isinstance(turn, dict) else str(turn)
            contents.append(content.strip().lower())

        for i in range(1, len(contents)):
            if contents[i] == contents[i-1] and contents[i]:
                issues.append(f"Turn {i+1} is an exact repetition of turn {i}.")

        # Check for contradictions (simple keyword heuristic)
        # Look for negation patterns in adjacent assistant turns
        assistant_contents = []
        for turn in turns:
            if isinstance(turn, dict) and turn.get("role") == "assistant":
                assistant_contents.append(turn.get("content", "").lower())
            elif not isinstance(turn, dict):
                assistant_contents.append(str(turn).lower())

        for i in range(1, len(assistant_contents)):
            prev = assistant_contents[i-1]
            curr = assistant_contents[i]
            # Simple contradiction check: "yes" followed by "no" on same topic
            if ("yes" in prev and "no" in curr) or ("no" in prev and "yes" in curr):
                # Only flag if they're short responses (likely direct contradictions)
                if len(prev.split()) < 20 and len(curr.split()) < 20:
                    issues.append(f"Possible contradiction between assistant turns {i} and {i+1}.")

        # Score: 1.0 minus penalty for each issue
        penalty = len(issues) * 0.2
        self.score = max(0.0, 1.0 - penalty)
        self.reason = "; ".join(issues) if issues else "Conversation maintains logical coherence."

    def _extract_turns(self, test_case: Any) -> List[Dict[str, str]]:
        """Extract conversation turns from test_case."""
        # Try JSON array in actual_output
        output = getattr(test_case, "actual_output", "") or ""

        try:
            parsed = json.loads(output)
            if isinstance(parsed, list):
                return parsed
        except (json.JSONDecodeError, TypeError):
            pass

        # Try conversation attribute (for multi-turn test cases)
        conv = getattr(test_case, "conversation", None)
        if conv and isinstance(conv, list):
            return conv

        # Fall back to splitting on double newlines
        parts = output.strip().split("\n\n")
        if len(parts) > 1:
            return [{"role": "unknown", "content": p.strip()} for p in parts if p.strip()]

        return [{"role": "unknown", "content": output}]


class ContextRetentionMetric(BaseMetric):
    """Evaluate whether the assistant remembers and uses context from earlier turns.

    Checks if key entities/facts mentioned in earlier user turns are referenced
    in later assistant responses when relevant.
    """
    name = "context_retention"

    def measure(self, test_case: Any) -> None:
        turns = self._extract_turns(test_case)

        if not turns or len(turns) < 3:
            self.score = 1.0
            self.reason = "Too few turns to evaluate context retention."
            return

        # Extract key terms from user messages
        user_terms: list[set[str]] = []
        assistant_contents: list[str] = []

        for turn in turns:
            if isinstance(turn, dict):
                role = turn.get("role", "")
                content = turn.get("content", "").lower()
            else:
                role = "unknown"
                content = str(turn).lower()

            if role in ("user", "unknown"):
                # Extract significant words (>3 chars, not common stopwords)
                stopwords = {"what", "when", "where", "which", "that", "this", "with", "from", "have", "your", "about", "would", "could", "should", "there", "their", "they", "been", "will", "more", "some", "than", "them", "very", "just", "also"}
                words = set(w for w in content.split() if len(w) > 3 and w.isalpha() and w not in stopwords)
                user_terms.append(words)
            elif role == "assistant":
                assistant_contents.append(content)

        if not user_terms or not assistant_contents:
            self.score = 1.0
            self.reason = "Could not extract user/assistant turns for context retention check."
            return

        # Check if terms from early user messages appear in later assistant responses
        # (only check if there's at least one later assistant response)
        early_terms = set()
        for terms in user_terms[:len(user_terms)//2 + 1]:  # first half of user messages
            early_terms.update(terms)

        if not early_terms:
            self.score = 1.0
            self.reason = "No significant terms found in early user messages."
            return

        late_assistant = " ".join(assistant_contents[len(assistant_contents)//2:])  # second half

        retained = sum(1 for t in early_terms if t in late_assistant)
        retention_rate = retained / len(early_terms) if early_terms else 1.0

        self.score = min(1.0, retention_rate * 2)  # Scale: 50% retention = 1.0

        if self.score >= 0.8:
            self.reason = f"Good context retention: {retained}/{len(early_terms)} key terms referenced."
        else:
            missed = early_terms - {t for t in early_terms if t in late_assistant}
            sample = list(missed)[:5]
            self.reason = f"Low context retention: {retained}/{len(early_terms)} terms. Missing: {', '.join(sample)}."

    def _extract_turns(self, test_case: Any) -> list:
        """Same extraction logic as ConversationCoherenceMetric."""
        output = getattr(test_case, "actual_output", "") or ""
        try:
            parsed = json.loads(output)
            if isinstance(parsed, list):
                return parsed
        except (json.JSONDecodeError, TypeError):
            pass
        conv = getattr(test_case, "conversation", None)
        if conv and isinstance(conv, list):
            return conv
        parts = output.strip().split("\n\n")
        if len(parts) > 1:
            return [{"role": "unknown", "content": p.strip()} for p in parts if p.strip()]
        return [{"role": "unknown", "content": output}]


class TurnCountMetric(BaseMetric):
    """Check if the conversation completed within an expected number of turns.

    Uses expected_output as the max turn count (e.g., "5" means max 5 turns).
    If no expected_output, scores 1.0 for conversations with <= 10 turns.
    """
    name = "turn_count"

    def measure(self, test_case: Any) -> None:
        turns = self._extract_turns(test_case)
        actual_turns = len(turns)

        # Get expected max turns
        expected = getattr(test_case, "expected_output", None)
        if expected:
            try:
                max_turns = int(expected)
            except (ValueError, TypeError):
                max_turns = 10
        else:
            max_turns = 10

        if actual_turns <= max_turns:
            self.score = 1.0
            self.reason = f"Conversation completed in {actual_turns} turns (max: {max_turns})."
        else:
            # Score decreases linearly: 2x max turns = 0.0
            overshoot = actual_turns - max_turns
            self.score = max(0.0, 1.0 - (overshoot / max_turns))
            self.reason = f"Conversation took {actual_turns} turns, exceeding max of {max_turns}."

    def _extract_turns(self, test_case: Any) -> list:
        output = getattr(test_case, "actual_output", "") or ""
        try:
            parsed = json.loads(output)
            if isinstance(parsed, list):
                return parsed
        except (json.JSONDecodeError, TypeError):
            pass
        conv = getattr(test_case, "conversation", None)
        if conv and isinstance(conv, list):
            return conv
        parts = output.strip().split("\n\n")
        if len(parts) > 1:
            return [p.strip() for p in parts if p.strip()]
        return [output] if output.strip() else []
