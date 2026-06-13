# ===
# File Summary
# Path: backend\apps\folders\templates.py
# Type: python
# Purpose: Folders domain handling templates, scans, change events, and review flows.
# Primary responsibilities:
# - Domain behavior is summarized for fast onboarding and avoids full-file reread.
# - Core symbols: RenderedFolderTemplate, paths, default_template_key, safe_path_segment, render_folder_template
# Inputs:
# - Downstream and upstream interactions in the same domain.
# Outputs:
# - API payloads, records, side effects, or UI views depending on file role.
# Dependencies:
# - Shared runtime services and adjacent domain modules.
# Known risks:
# - Validate behavior after migrations, dependency upgrades, or contract changes.
# ===
# 

from dataclasses import dataclass
import re


PRODUCT_TEMPLATE_KEY = "product_standard"
RAW_MATERIAL_TEMPLATE_KEY = "raw_material_standard"
PROJECT_TEMPLATE_KEY = "project_standard"
SUPPLIER_TEMPLATE_KEY = "supplier_standard"


@dataclass(frozen=True)
class RenderedFolderTemplate:
    root: str
    children: list[str]

    @property
    def paths(self):
        return [self.root, *self.children]


TEMPLATE_CHILDREN = {
    PRODUCT_TEMPLATE_KEY: [
        "01_Specifications",
        "02_Drawings",
        "03_Materials",
        "04_Testing",
        "05_Project_Files",
        "99_Working",
    ],
    RAW_MATERIAL_TEMPLATE_KEY: [
        "01_Supplier_Documents",
        "02_Technical_Data",
        "03_Compliance",
        "99_Working",
    ],
    PROJECT_TEMPLATE_KEY: [
        "01_Charter",
        "02_Gate_Reviews",
        "03_Trials",
        "04_Customer_Inputs",
        "99_Working",
    ],
    SUPPLIER_TEMPLATE_KEY: [
        "01_Qualification",
        "02_Compliance",
        "03_Correspondence",
        "99_Working",
    ],
}

TEMPLATE_ROOTS = {
    PRODUCT_TEMPLATE_KEY: "Products",
    RAW_MATERIAL_TEMPLATE_KEY: "Raw_Materials",
    PROJECT_TEMPLATE_KEY: "Projects",
    SUPPLIER_TEMPLATE_KEY: "Suppliers",
}

DEFAULT_TEMPLATE_BY_OBJECT_TYPE = {
    "product": PRODUCT_TEMPLATE_KEY,
    "raw_material": RAW_MATERIAL_TEMPLATE_KEY,
    "project": PROJECT_TEMPLATE_KEY,
    "supplier": SUPPLIER_TEMPLATE_KEY,
}


def default_template_key(object_type_key):
    return DEFAULT_TEMPLATE_BY_OBJECT_TYPE.get(object_type_key)


def safe_path_segment(value):
    segment = str(value or "").strip()
    segment = segment.replace("/", "_").replace("\\", "_")
    segment = re.sub(r"[^A-Za-z0-9._-]+", "_", segment)
    segment = re.sub(r"_+", "_", segment).strip("._-")
    return segment or "untitled"


def render_folder_template(record, template_key=None):
    template_key = template_key or default_template_key(record.object_type_key)
    if template_key not in TEMPLATE_CHILDREN:
        raise ValueError(f"No managed folder template for {record.object_type_key}.")

    root_name = TEMPLATE_ROOTS[template_key]
    record_folder = f"{safe_path_segment(record.code)}_{safe_path_segment(record.title)}"
    root = f"{root_name}/{record_folder}"
    children = [f"{root}/{child}" for child in TEMPLATE_CHILDREN[template_key]]
    return RenderedFolderTemplate(root=root, children=children)

