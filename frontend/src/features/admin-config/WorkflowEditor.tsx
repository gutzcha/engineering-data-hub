import { useState } from "react";

import type { WorkflowDefinition } from "./ConfigWorkspace";

type WorkflowEditorProps = {
  workflow: WorkflowDefinition;
  readOnly: boolean;
  onChange: (workflow: WorkflowDefinition) => void;
};

type WorkflowTransition = NonNullable<WorkflowDefinition["transitions"]>[number];

export function WorkflowEditor({ workflow, readOnly, onChange }: WorkflowEditorProps) {
  const [selectedTransitionIndex, setSelectedTransitionIndex] = useState(0);
  const transitions = normalizeTransitions(workflow.transitions);
  const safeSelectedIndex = Math.min(selectedTransitionIndex, transitions.length - 1);
  const transition = transitions[safeSelectedIndex];

  function updateSelectedTransition(update: Partial<WorkflowTransition>) {
    const updatedTransitions = transitions.map((candidate, index) =>
      index === safeSelectedIndex ? { ...candidate, ...update } : candidate
    );
    onChange({ ...workflow, transitions: updatedTransitions });
  }

  function addTransition() {
    const newTransition = {
      from: transition.to,
      to: "released",
      guard: "",
      task_template: ""
    };
    onChange({ ...workflow, transitions: [...transitions, newTransition] });
    setSelectedTransitionIndex(transitions.length);
  }

  function removeTransition() {
    if (transitions.length <= 1) {
      return;
    }

    const updatedTransitions = transitions.filter(
      (_candidate, index) => index !== safeSelectedIndex
    );
    onChange({ ...workflow, transitions: updatedTransitions });
    setSelectedTransitionIndex(Math.max(0, safeSelectedIndex - 1));
  }

  return (
    <section className="table-panel admin-panel" aria-labelledby="workflow-title">
      <div className="panel-heading">
        <div>
          <p className="section-kicker">Lifecycle controls</p>
          <h2 id="workflow-title">Workflow Editor</h2>
        </div>
      </div>
      <div className="admin-panel-body editor-stack">
        <div className="admin-form-grid">
          <label className="field-control">
            <span>Workflow key</span>
            <input
              value={workflow.key}
              disabled={readOnly}
              onChange={(event) => onChange({ ...workflow, key: event.target.value })}
            />
          </label>
          <label className="field-control">
            <span>Workflow label</span>
            <input
              value={workflow.label ?? ""}
              disabled={readOnly}
              onChange={(event) => onChange({ ...workflow, label: event.target.value })}
            />
          </label>
          <label className="field-control field-control-wide">
            <span>States</span>
            <input
              value={(workflow.states ?? []).join(", ")}
              disabled={readOnly}
              onChange={(event) =>
                onChange({ ...workflow, states: splitList(event.target.value) })
              }
            />
          </label>
          <label className="field-control">
            <span>Selected transition</span>
            <select
              value={safeSelectedIndex.toString()}
              disabled={readOnly}
              onChange={(event) => setSelectedTransitionIndex(Number(event.target.value))}
            >
              {transitions.map((candidate, index) => (
                <option key={`${candidate.from}-${candidate.to}-${index}`} value={index}>
                  {index + 1}: {candidate.from} to {candidate.to}
                </option>
              ))}
            </select>
          </label>
          <div className="workflow-transition-actions">
            <button
              className="button button-secondary"
              type="button"
              onClick={addTransition}
              disabled={readOnly}
            >
              Add Transition
            </button>
            <button
              className="button button-secondary"
              type="button"
              onClick={removeTransition}
              disabled={readOnly || transitions.length <= 1}
            >
              Remove Transition
            </button>
          </div>
          <label className="field-control">
            <span>Transition from</span>
            <input
              value={transition.from}
              disabled={readOnly}
              onChange={(event) => updateSelectedTransition({ from: event.target.value })}
            />
          </label>
          <label className="field-control">
            <span>Transition to</span>
            <input
              value={transition.to}
              disabled={readOnly}
              onChange={(event) => updateSelectedTransition({ to: event.target.value })}
            />
          </label>
          <label className="field-control">
            <span>Guards</span>
            <input
              value={transition.guard ?? ""}
              disabled={readOnly}
              onChange={(event) => updateSelectedTransition({ guard: event.target.value })}
            />
          </label>
          <label className="field-control">
            <span>Task templates</span>
            <input
              value={transition.task_template ?? ""}
              disabled={readOnly}
              onChange={(event) =>
                updateSelectedTransition({ task_template: event.target.value })
              }
            />
          </label>
          <label className="field-control field-control-wide">
            <span>Release rules</span>
            <input
              value={(workflow.release_rules ?? []).join(", ")}
              disabled={readOnly}
              onChange={(event) =>
                onChange({ ...workflow, release_rules: splitList(event.target.value) })
              }
            />
          </label>
        </div>
      </div>
    </section>
  );
}

function normalizeTransitions(transitions: WorkflowDefinition["transitions"]) {
  return transitions && transitions.length > 0
    ? transitions
    : [
        {
          from: "draft",
          to: "review",
          guard: "required_fields_complete",
          task_template: "Engineering review"
        }
      ];
}

function splitList(value: string) {
  return value
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
}
