import { useMutation, useQuery } from "@tanstack/react-query";
import { AlertTriangle, Loader2, Plus, Save } from "lucide-react";
import type { FormEvent } from "react";
import { useEffect, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";

import { StatusBadge } from "../../components/StatusBadge";
import { apiGet, apiPost } from "../../lib/api";
import {
  ConfigData,
  DynamicRecordForm,
  ObjectTypeDefinition,
  RecordValues
} from "./DynamicRecordForm";

type ConfigVersion = {
  data?: ConfigData;
};

type CreatedRecord = {
  id: string | number;
  object_type_key: string;
  code?: string;
  title?: string;
  data?: RecordValues;
};

export function RecordCreate() {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const [values, setValues] = useState<RecordValues>({});
  const requestedObjectType = searchParams.get("object_type_key") ?? "";

  const configQuery = useQuery({
    queryKey: ["config", "active"],
    queryFn: () => apiGet<ConfigVersion>("/config/active/")
  });

  const objectTypes = configQuery.data?.data?.object_types ?? [];
  const selectedObjectType =
    objectTypes.find((objectType) => objectType.key === requestedObjectType) ?? objectTypes[0];
  const selectedObjectTypeKey = selectedObjectType?.key ?? "";

  const createRecord = useMutation({
    mutationFn: () =>
      apiPost<CreatedRecord>("/records/", {
        object_type_key: selectedObjectTypeKey,
        data: compactValues(values)
      }),
    onSuccess: (record) => navigate(`/records/${record.id}`)
  });

  useEffect(() => {
    if (!requestedObjectType && selectedObjectTypeKey) {
      setSearchParams({ object_type_key: selectedObjectTypeKey }, { replace: true });
    }
  }, [requestedObjectType, selectedObjectTypeKey, setSearchParams]);

  function changeObjectType(nextObjectType: string) {
    setValues({});
    setSearchParams({ object_type_key: nextObjectType });
  }

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (selectedObjectTypeKey && !createRecord.isPending) {
      createRecord.mutate();
    }
  }

  return (
    <div className="page-stack record-detail">
      <section className="workspace-header" aria-labelledby="record-create-title">
        <div>
          <p className="section-kicker">Material, trial, and test records</p>
          <h1 id="record-create-title">New Record</h1>
        </div>
        <StatusBadge tone={selectedObjectTypeKey ? "review" : "neutral"}>
          {labelForObjectType(selectedObjectType)}
        </StatusBadge>
      </section>

      {(configQuery.error || createRecord.error) && (
        <div className="admin-alert" role="alert">
          <strong>{createRecord.error ? "Record creation failed" : "Configuration failed"}</strong>
          <span>{errorMessage(createRecord.error ?? configQuery.error)}</span>
        </div>
      )}

      <section className="table-panel detail-panel" aria-labelledby="record-create-form-title">
        <div className="panel-heading">
          <div>
            <p className="section-kicker">Draft record</p>
            <h2 id="record-create-form-title">Record Fields</h2>
          </div>
          {configQuery.isLoading ? (
            <Loader2 aria-hidden="true" size={18} />
          ) : (
            <Plus aria-hidden="true" size={18} />
          )}
        </div>
        <form className="record-panel-body record-create-form" onSubmit={submit}>
          <label className="field-control">
            <span>Object type</span>
            <select
              aria-label="Object type"
              value={selectedObjectTypeKey}
              disabled={configQuery.isLoading || createRecord.isPending}
              required
              onChange={(event) => changeObjectType(event.target.value)}
            >
              {objectTypes.map((objectType) => (
                <option key={objectType.key} value={objectType.key}>
                  {labelForObjectType(objectType)}
                </option>
              ))}
            </select>
          </label>

          {objectTypes.length === 0 && !configQuery.isLoading ? (
            <div className="empty-state" role="alert">
              <AlertTriangle aria-hidden="true" size={24} />
              <div>
                <h2>No published object types</h2>
                <p>Publish a configuration before creating records.</p>
              </div>
            </div>
          ) : (
            <DynamicRecordForm
              config={configQuery.data?.data}
              objectTypeKey={selectedObjectTypeKey}
              values={values}
              onChange={setValues}
            />
          )}

          <div className="record-action-row record-create-actions">
            <button
              className="button button-primary"
              type="submit"
              disabled={!selectedObjectTypeKey || configQuery.isLoading || createRecord.isPending}
            >
              {createRecord.isPending ? (
                <Loader2 aria-hidden="true" size={16} />
              ) : (
                <Save aria-hidden="true" size={16} />
              )}
              Create Record
            </button>
          </div>
        </form>
      </section>
    </div>
  );
}

function compactValues(values: RecordValues) {
  return Object.fromEntries(
    Object.entries(values).filter(([, value]) => {
      if (value === undefined || value === null || value === "") {
        return false;
      }

      return !(Array.isArray(value) && value.length === 0);
    })
  );
}

function labelForObjectType(objectType?: ObjectTypeDefinition) {
  return objectType?.label ?? objectType?.plural_label ?? objectType?.key ?? "Record";
}

function errorMessage(error: unknown) {
  return error instanceof Error ? error.message : "Record creation request failed.";
}
