from __future__ import annotations

from enum import Enum


class DocumentWorkflowState(str, Enum):
    UPLOADED = "UPLOADED"
    INSPECTING = "INSPECTING"
    READY_FOR_EXTRACTION = "READY_FOR_EXTRACTION"
    EXTRACTING = "EXTRACTING"
    EXTRACTED = "EXTRACTED"
    MATCHING = "MATCHING"
    VALIDATING = "VALIDATING"
    NEEDS_REVIEW = "NEEDS_REVIEW"
    VERIFIED = "VERIFIED"
    PUBLISHED = "PUBLISHED"
    RETRYABLE_ERROR = "RETRYABLE_ERROR"
    PERMANENT_ERROR = "PERMANENT_ERROR"
    QUARANTINED = "QUARANTINED"


_ALLOWED_TRANSITIONS: dict[DocumentWorkflowState, set[DocumentWorkflowState]] = {
    DocumentWorkflowState.UPLOADED: {
        DocumentWorkflowState.INSPECTING,
        DocumentWorkflowState.QUARANTINED,
        DocumentWorkflowState.PERMANENT_ERROR,
    },
    DocumentWorkflowState.INSPECTING: {
        DocumentWorkflowState.READY_FOR_EXTRACTION,
        DocumentWorkflowState.RETRYABLE_ERROR,
        DocumentWorkflowState.PERMANENT_ERROR,
        DocumentWorkflowState.QUARANTINED,
    },
    DocumentWorkflowState.READY_FOR_EXTRACTION: {
        DocumentWorkflowState.EXTRACTING,
        DocumentWorkflowState.RETRYABLE_ERROR,
    },
    DocumentWorkflowState.EXTRACTING: {
        DocumentWorkflowState.EXTRACTED,
        DocumentWorkflowState.RETRYABLE_ERROR,
        DocumentWorkflowState.PERMANENT_ERROR,
    },
    DocumentWorkflowState.EXTRACTED: {
        DocumentWorkflowState.MATCHING,
        DocumentWorkflowState.NEEDS_REVIEW,
        DocumentWorkflowState.PERMANENT_ERROR,
    },
    DocumentWorkflowState.MATCHING: {
        DocumentWorkflowState.VALIDATING,
        DocumentWorkflowState.NEEDS_REVIEW,
        DocumentWorkflowState.RETRYABLE_ERROR,
        DocumentWorkflowState.PERMANENT_ERROR,
    },
    DocumentWorkflowState.VALIDATING: {
        DocumentWorkflowState.NEEDS_REVIEW,
        DocumentWorkflowState.VERIFIED,
        DocumentWorkflowState.PERMANENT_ERROR,
    },
    DocumentWorkflowState.NEEDS_REVIEW: {
        DocumentWorkflowState.VERIFIED,
        DocumentWorkflowState.PERMANENT_ERROR,
    },
    DocumentWorkflowState.VERIFIED: {
        DocumentWorkflowState.PUBLISHED,
        DocumentWorkflowState.NEEDS_REVIEW,
    },
    DocumentWorkflowState.PUBLISHED: set(),
    DocumentWorkflowState.RETRYABLE_ERROR: {
        DocumentWorkflowState.INSPECTING,
        DocumentWorkflowState.READY_FOR_EXTRACTION,
        DocumentWorkflowState.EXTRACTING,
        DocumentWorkflowState.MATCHING,
        DocumentWorkflowState.PERMANENT_ERROR,
    },
    DocumentWorkflowState.PERMANENT_ERROR: set(),
    DocumentWorkflowState.QUARANTINED: set(),
}


class InvalidWorkflowTransition(ValueError):
    def __init__(self, current: DocumentWorkflowState, target: DocumentWorkflowState) -> None:
        super().__init__(f"Invalid document workflow transition: {current.value} -> {target.value}")
        self.current = current
        self.target = target


def transition_document_state(
    current: DocumentWorkflowState,
    target: DocumentWorkflowState,
) -> DocumentWorkflowState:
    if target == current:
        return current
    if target not in _ALLOWED_TRANSITIONS[current]:
        raise InvalidWorkflowTransition(current=current, target=target)
    return target
