from __future__ import annotations

import pytest
from medarchive_domain.workflow import (
    DocumentWorkflowState,
    InvalidWorkflowTransition,
    transition_document_state,
)


def test_valid_document_transition() -> None:
    assert (
        transition_document_state(
            DocumentWorkflowState.UPLOADED,
            DocumentWorkflowState.INSPECTING,
        )
        == DocumentWorkflowState.INSPECTING
    )


def test_invalid_document_transition_is_rejected() -> None:
    with pytest.raises(InvalidWorkflowTransition):
        transition_document_state(
            DocumentWorkflowState.UPLOADED,
            DocumentWorkflowState.PUBLISHED,
        )
