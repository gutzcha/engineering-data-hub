def starter_configuration_data():
    object_types = [
        {
            "key": "product",
            "label": "Product",
            "plural_label": "Products",
            "code_pattern": "PROD-{seq:000000}",
            "title_field": "commercial_name",
            "folder_template_key": "product_standard",
            "default_workflow_key": "engineering_release",
            "is_system": True,
            "fields": [
                {
                    "key": "commercial_name",
                    "label": "Commercial Name",
                    "type": "text",
                    "required": True,
                }
            ],
        },
        {
            "key": "raw_material",
            "label": "Raw Material",
            "plural_label": "Raw Materials",
            "code_pattern": "RM-{seq:000000}",
            "title_field": "material_name",
            "folder_template_key": "raw_material_standard",
            "default_workflow_key": "engineering_release",
            "is_system": True,
            "fields": [
                {"key": "material_name", "label": "Material Name", "type": "text", "required": True}
            ],
        },
        {
            "key": "product_spec",
            "label": "Product Spec",
            "plural_label": "Product Specs",
            "code_pattern": "SPEC-{seq:000000}",
            "title_field": "spec_name",
            "folder_template_key": "spec_standard",
            "default_workflow_key": "engineering_release",
            "is_system": True,
            "fields": [
                {"key": "spec_name", "label": "Spec Name", "type": "text", "required": True}
            ],
        },
        {
            "key": "supplier",
            "label": "Supplier",
            "plural_label": "Suppliers",
            "code_pattern": "SUP-{seq:000000}",
            "title_field": "supplier_name",
            "folder_template_key": "supplier_standard",
            "default_workflow_key": "supplier_approval",
            "is_system": True,
            "fields": [
                {
                    "key": "supplier_name",
                    "label": "Supplier Name",
                    "type": "text",
                    "required": True,
                }
            ],
        },
        {
            "key": "customer",
            "label": "Customer",
            "plural_label": "Customers",
            "code_pattern": "CUS-{seq:000000}",
            "title_field": "customer_name",
            "folder_template_key": "customer_standard",
            "default_workflow_key": "customer_approval",
            "is_system": True,
            "fields": [
                {
                    "key": "customer_name",
                    "label": "Customer Name",
                    "type": "text",
                    "required": True,
                }
            ],
        },
        {
            "key": "project",
            "label": "Project",
            "plural_label": "Projects",
            "code_pattern": "PRJ-{seq:000000}",
            "title_field": "project_name",
            "folder_template_key": "project_standard",
            "default_workflow_key": "project_stage_gate",
            "is_system": True,
            "fields": [
                {"key": "project_name", "label": "Project Name", "type": "text", "required": True}
            ],
        },
        {
            "key": "test_method",
            "label": "Test Method",
            "plural_label": "Test Methods",
            "code_pattern": "TM-{seq:000000}",
            "title_field": "method_name",
            "folder_template_key": "test_method_standard",
            "default_workflow_key": "engineering_release",
            "is_system": True,
            "fields": [
                {"key": "method_name", "label": "Method Name", "type": "text", "required": True}
            ],
        },
        {
            "key": "document",
            "label": "Document",
            "plural_label": "Documents",
            "code_pattern": "DOC-{seq:000000}",
            "title_field": "document_title",
            "folder_template_key": "document_standard",
            "default_workflow_key": "document_release",
            "is_system": True,
            "fields": [
                {
                    "key": "document_title",
                    "label": "Document Title",
                    "type": "text",
                    "required": True,
                }
            ],
        },
    ]

    relationship_types = [
        {
            "key": "product_uses_material",
            "label": "Product uses material",
            "source_object_type": "product",
            "target_object_type": "raw_material",
        },
        {
            "key": "product_has_spec",
            "label": "Product has spec",
            "source_object_type": "product",
            "target_object_type": "product_spec",
        },
        {
            "key": "project_affects_product",
            "label": "Project affects product",
            "source_object_type": "project",
            "target_object_type": "product",
        },
        {
            "key": "supplier_provides_material",
            "label": "Supplier provides material",
            "source_object_type": "supplier",
            "target_object_type": "raw_material",
        },
        {
            "key": "customer_uses_product",
            "label": "Customer uses product",
            "source_object_type": "customer",
            "target_object_type": "product",
        },
        {
            "key": "document_attached_to_record",
            "label": "Document attached to record",
            "source_object_type": "document",
        },
    ]

    return {
        "object_types": object_types,
        "relationship_types": relationship_types,
        "form_layouts": [],
        "folder_templates": [],
        "dashboards": [],
    }
