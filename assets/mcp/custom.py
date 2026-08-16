from __future__ import annotations

import logging
import os
from datetime import date
from typing import TYPE_CHECKING, Annotated, Any, Literal

from fastmcp import FastMCP
from fastmcp.server.dependencies import get_http_headers
from mcp.server.lowlevel.server import request_ctx
from pydantic import BaseModel, Field
from snipeit import SnipeIT
from snipeit.exceptions import (
    SnipeITAuthenticationError,
    SnipeITException,
    SnipeITNotFoundError,
    SnipeITValidationError,
)

if TYPE_CHECKING:
    from server import SnipeITDirectAPI


logger = logging.getLogger(__name__)


def get_app_url_and_token() -> tuple[str, str]:
    """Extract application URL and token from request headers.

    Returns:
        Tuple of (app_url, token)

    Raises:
        ValueError: If authorization token or host header is missing
    """
    # Get headers (returns empty dict if no request context)
    headers = get_http_headers()
    logger.debug(f"Received request with headers: {headers}")

    # Try to get the raw request from context to access Authorization header
    auth_header = ""
    try:
        ctx = request_ctx.get(None)
        if ctx and hasattr(ctx, "request") and ctx.request:
            auth_header = ctx.request.headers.get("authorization", "")
            logger.debug(
                f"Found authorization header from request context: {bool(auth_header)}"
            )
        else:
            logger.debug("No request context available, trying headers dict")
            auth_header = headers.get("authorization", "")
    except Exception as e:
        logger.debug(f"Could not access request context: {e}")
        auth_header = headers.get("authorization", "")

    is_bearer = auth_header.casefold().startswith("bearer ")

    token = None
    if auth_header and is_bearer:
        token = auth_header[7:].strip()  # Skip "Bearer " prefix (case-insensitive)
    if not token:
        logger.error("Missing or invalid Authorization token")
        raise ValueError("Missing or invalid Authorization token in request headers")
    logger.debug(f"Extracted token: {'[REDACTED]' if token else 'None'}")

    # Determine Application URL from headers
    app_host = headers.get("x-forwarded-host") or headers.get("host")
    if app_host:
        logger.debug(f"Extracted app host: {app_host}")

        # Optionally, set scheme (default to https if x-forwarded-proto is set, else http)
        scheme = headers.get("x-forwarded-proto", "http")
        app_url = f"{scheme}://{app_host}"
    else:
        app_url = os.getenv("SNIPEIT_URL", "").strip()
        if not app_url:
            logger.error("No host header found in request and SNIPEIT_URL is unset")
            raise ValueError("No host header found in request")
        logger.debug("Falling back to SNIPEIT_URL for app URL")

    logger.debug(f"Constructed app URL: {app_url}")
    return app_url.rstrip("/"), token


def update_direct_client(client: SnipeITDirectAPI) -> None:
    """Update the App URL and token from data in the request headers.

    Args:
        client: HTTP client object to update with credentials
    """
    app_url, token = get_app_url_and_token()
    # set these vars that control the REST client in server.py
    client.base_url = app_url
    client.headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    logger.debug(f"Updated client with URL: {app_url} and token: [REDACTED]")


def get_snipe_client() -> SnipeIT:
    """Create a SnipeIT client using credentials from request headers.

    Returns:
        Configured SnipeIT client instance
    """
    app_url, token = get_app_url_and_token()
    logger.debug(f"Creating SnipeIT client for URL: {app_url}")
    return SnipeIT(url=app_url, token=token)


def run_custom_http_server(mcp: FastMCP) -> None:
    """Add recommended stateless config for Copilot"""
    logger = logging.getLogger(__name__)

    # Register the custom maintenance tool used by this server build.
    try:
        mcp.local_provider.remove_tool("asset_maintenance")
    except Exception:
        logger.warning(
            "Failed to remove existing asset_maintenance tool (may not exist)"
        )
    mcp.add_tool(asset_maintenance)
    mcp.add_tool(manage_maintenance_types)

    logger.info("Starting custom stateless HTTP transport")
    mcp.run(
        transport="http",
        port=int(os.getenv("PORT", "8001")),
        host=os.getenv("HOST", "0.0.0.0"),
        stateless_http=True,
    )


# ---------------------------------------------------------------------------
# Extended asset_maintenance tool – replaces the create-only version in server.py
# ---------------------------------------------------------------------------


class MaintenanceData(BaseModel):
    """Maintenance record data supporting both create and update operations."""

    # Create fields (used by the snipeit library)
    asset_improvement: str | None = Field(
        None, description="Maintenance type string (for create, e.g. 'Repair')"
    )
    title: str | None = Field(None, description="Maintenance title (for create)")
    # Update fields (used by the direct API)
    name: str | None = Field(None, description="Maintenance name/title (for update)")
    maintenance_type_id: int | None = Field(
        None, description="Maintenance type ID (required for update)"
    )
    is_warranty: bool | None = Field(
        None, description="Whether this is a warranty repair"
    )
    # Shared fields
    asset_id: int | None = Field(None, description="Asset ID (required for PUT update)")
    supplier_id: int | None = Field(None, description="Supplier ID (optional)")
    cost: float | None = Field(None, description="Maintenance cost")
    start_date: str | None = Field(None, description="Start date (YYYY-MM-DD)")
    expected_completion_date: str | None = Field(
        None, description="Expected completion date (YYYY-MM-DD)"
    )
    completion_date: str | None = Field(
        None, description="Completion date (YYYY-MM-DD)"
    )
    notes: str | None = Field(None, description="Maintenance notes")


def _is_valid_date_yyyy_mm_dd(value: str) -> bool:
    """Return True when value matches YYYY-MM-DD."""
    try:
        date.fromisoformat(value)
        return True
    except ValueError:
        return False


def asset_maintenance(
    action: Annotated[
        Literal["create", "list", "get", "update", "delete", "complete"],
        "The maintenance operation to perform",
    ],
    asset_id: Annotated[
        int | None, "Asset ID (required for create; optional filter for list)"
    ] = None,
    maintenance_id: Annotated[
        int | None, "Maintenance record ID (required for get, update, delete)"
    ] = None,
    maintenance_data: Annotated[
        dict[str, Any] | None,
        "Maintenance record data (required for create and update)",
    ] = None,
    limit: Annotated[int | None, "Number of results to return (for list action)"] = 50,
    offset: Annotated[int | None, "Number of results to skip (for list action)"] = 0,
    search: Annotated[str | None, "Search query (for list action)"] = None,
    sort: Annotated[str | None, "Field to sort by (for list action)"] = None,
    order: Annotated[
        Literal["asc", "desc"] | None, "Sort order (for list action)"
    ] = None,
) -> dict[str, Any]:
    """Manage maintenance records for assets.

        Operations:
        - create: Create a new maintenance record.
            Required by API docs: name/title, asset_id, supplier_id, maintenance_type_id, start_date.
            Optional: is_warranty, cost, notes, expected_completion_date, completion_date.
        - list: List maintenance records with optional asset_id filter, pagination, and search.
        - get: Retrieve a single maintenance record by maintenance_id.
        - update: Patch a maintenance record.
            Required by API docs: maintenance_type_id.
            Optional: name, asset_id, supplier_id, is_warranty, cost, notes, start_date, expected_completion_date, completion_date.
        - delete: Delete a maintenance record by maintenance_id.
        - complete: Mark a maintenance record complete by maintenance_id.
            Optional: completion_date and notes.

    Returns:
        dict: Result of the operation including success status and data
    """
    # lazy import to avoid circular dependency (server imports custom at module level)
    from server import get_direct_api

    try:
        if action == "create":
            if not asset_id:
                return {
                    "success": False,
                    "error": "asset_id is required for create action",
                }
            if not maintenance_data:
                return {
                    "success": False,
                    "error": "maintenance_data is required for create action",
                }

            parsed = MaintenanceData.model_validate(maintenance_data)
            title = parsed.title or parsed.name
            if not title:
                return {
                    "success": False,
                    "error": "name/title is required for create action",
                }
            if parsed.asset_id is not None and parsed.asset_id != asset_id:
                return {
                    "success": False,
                    "error": "asset_id in maintenance_data must match top-level asset_id",
                }
            if parsed.supplier_id and parsed.supplier_id <= 0:
                return {
                    "success": False,
                    "error": "supplier_id must be a positive integer",
                }
            if parsed.maintenance_type_id is None:
                return {
                    "success": False,
                    "error": "maintenance_type_id is required for create action",
                }
            if parsed.maintenance_type_id <= 0:
                return {
                    "success": False,
                    "error": "maintenance_type_id must be a positive integer",
                }
            if not parsed.start_date:
                return {
                    "success": False,
                    "error": "start_date is required for create action",
                }
            if not _is_valid_date_yyyy_mm_dd(parsed.start_date):
                return {
                    "success": False,
                    "error": "start_date must be in YYYY-MM-DD format",
                }
            if parsed.completion_date and not _is_valid_date_yyyy_mm_dd(
                parsed.completion_date
            ):
                return {
                    "success": False,
                    "error": "completion_date must be in YYYY-MM-DD format",
                }
            if parsed.expected_completion_date and not _is_valid_date_yyyy_mm_dd(
                parsed.expected_completion_date
            ):
                return {
                    "success": False,
                    "error": "expected_completion_date must be in YYYY-MM-DD format",
                }

            api = get_direct_api()
            create_payload: dict[str, Any] = {
                "asset_id": asset_id,
                "title": title,
                "name": title,
                "supplier_id": parsed.supplier_id,
                "maintenance_type_id": parsed.maintenance_type_id,
                "start_date": parsed.start_date,
            }

            # Keep compatibility with instances that still inspect maintenance type string fields.
            maintenance_type = parsed.asset_improvement or "Maintenance"
            create_payload["asset_improvement"] = maintenance_type
            create_payload["asset_maintenance_type"] = maintenance_type

            if parsed.is_warranty is not None:
                create_payload["is_warranty"] = parsed.is_warranty
            if parsed.cost is not None:
                create_payload["cost"] = parsed.cost
            if parsed.completion_date:
                create_payload["completion_date"] = parsed.completion_date
            if parsed.expected_completion_date:
                create_payload["expected_completion_date"] = (
                    parsed.expected_completion_date
                )
            if parsed.notes:
                create_payload["notes"] = parsed.notes

            result = api._request("POST", "maintenances", json=create_payload)
            if isinstance(result, dict) and result.get("status") == "error":
                return {
                    "success": False,
                    "action": "create",
                    "asset_id": asset_id,
                    "error": "Validation error",
                    "details": result.get("messages", result),
                }
            return {
                "success": True,
                "action": "create",
                "asset_id": asset_id,
                "message": "Maintenance record created successfully",
                "maintenance": result,
            }

        elif action == "list":
            api = get_direct_api()
            params: dict[str, Any] = {"limit": limit or 50, "offset": offset or 0}
            if asset_id:
                params["asset_id"] = asset_id
            if search:
                params["search"] = search
            if sort:
                params["sort"] = sort
            if order:
                params["order"] = order

            result = api._request("GET", "maintenances", params=params)
            records = result.get("rows", [])
            return {
                "success": True,
                "action": "list",
                "total": result.get("total", len(records)),
                "count": len(records),
                "maintenances": records,
            }

        elif action == "get":
            if not maintenance_id:
                return {
                    "success": False,
                    "error": "maintenance_id is required for get action",
                }

            api = get_direct_api()
            result = api._request("GET", f"maintenances/{maintenance_id}")
            return {"success": True, "action": "get", "maintenance": result}

        elif action == "update":
            if not maintenance_id:
                return {
                    "success": False,
                    "error": "maintenance_id is required for update action",
                }
            if not maintenance_data:
                return {
                    "success": False,
                    "error": "maintenance_data is required for update action",
                }

            parsed = MaintenanceData.model_validate(maintenance_data)
            if parsed.maintenance_type_id is None:
                return {
                    "success": False,
                    "error": "maintenance_type_id is required for update action",
                }
            if parsed.maintenance_type_id <= 0:
                return {
                    "success": False,
                    "error": "maintenance_type_id must be a positive integer",
                }
            if parsed.start_date and not _is_valid_date_yyyy_mm_dd(parsed.start_date):
                return {
                    "success": False,
                    "error": "start_date must be in YYYY-MM-DD format",
                }
            if parsed.completion_date and not _is_valid_date_yyyy_mm_dd(
                parsed.completion_date
            ):
                return {
                    "success": False,
                    "error": "completion_date must be in YYYY-MM-DD format",
                }
            if parsed.expected_completion_date and not _is_valid_date_yyyy_mm_dd(
                parsed.expected_completion_date
            ):
                return {
                    "success": False,
                    "error": "expected_completion_date must be in YYYY-MM-DD format",
                }
            if parsed.supplier_id is not None and parsed.supplier_id <= 0:
                return {
                    "success": False,
                    "error": "supplier_id must be a positive integer when provided",
                }

            # Keep update payload minimal: only pass user-provided fields.
            allowed_update_fields = {
                "name",
                "asset_id",
                "supplier_id",
                "is_warranty",
                "cost",
                "notes",
                "maintenance_type_id",
                "start_date",
                "expected_completion_date",
                "completion_date",
            }
            update_payload = {
                k: v
                for k, v in parsed.model_dump().items()
                if v is not None and k in allowed_update_fields
            }
            if "title" in maintenance_data and "name" not in update_payload:
                update_payload["name"] = maintenance_data["title"]

            if not update_payload:
                return {
                    "success": False,
                    "error": "At least one updatable field must be provided",
                }

            api = get_direct_api()
            result = api._request(
                "PATCH", f"maintenances/{maintenance_id}", json=update_payload
            )
            return {
                "success": True,
                "action": "update",
                "maintenance_id": maintenance_id,
                "message": "Maintenance record updated successfully",
                "maintenance": result,
            }

        elif action == "delete":
            if not maintenance_id:
                return {
                    "success": False,
                    "error": "maintenance_id is required for delete action",
                }

            api = get_direct_api()
            api._request("DELETE", f"maintenances/{maintenance_id}")
            return {
                "success": True,
                "action": "delete",
                "maintenance_id": maintenance_id,
                "message": "Maintenance record deleted successfully",
            }

        elif action == "complete":
            if not maintenance_id:
                return {
                    "success": False,
                    "error": "maintenance_id is required for complete action",
                }

            completion_payload: dict[str, Any] = {}
            if maintenance_data:
                parsed = MaintenanceData.model_validate(maintenance_data)
                if parsed.completion_date and not _is_valid_date_yyyy_mm_dd(
                    parsed.completion_date
                ):
                    return {
                        "success": False,
                        "error": "completion_date must be in YYYY-MM-DD format",
                    }
                if parsed.completion_date:
                    completion_payload["completion_date"] = parsed.completion_date
                if parsed.notes:
                    completion_payload["notes"] = parsed.notes

            api = get_direct_api()
            result = api._request(
                "POST",
                f"maintenances/{maintenance_id}/complete",
                json=completion_payload,
            )
            return {
                "success": True,
                "action": "complete",
                "maintenance_id": maintenance_id,
                "message": "Maintenance record completed successfully",
                "maintenance": result,
            }

        return {"success": False, "error": f"Unknown action: {action}"}

    except SnipeITNotFoundError as e:
        logging.getLogger(__name__).error(f"Maintenance record not found: {e}")
        return {"success": False, "error": f"Not found: {str(e)}"}
    except SnipeITAuthenticationError as e:
        logging.getLogger(__name__).error(f"Authentication error: {e}")
        return {"success": False, "error": f"Authentication failed: {str(e)}"}
    except SnipeITValidationError as e:
        logging.getLogger(__name__).error(f"Validation error: {e}")
        return {"success": False, "error": f"Validation error: {str(e)}"}
    except SnipeITException as e:
        logging.getLogger(__name__).error(f"Snipe-IT error: {e}")
        return {"success": False, "error": f"Snipe-IT error: {str(e)}"}
    except Exception as e:
        logging.getLogger(__name__).exception("Unexpected error in asset_maintenance")
        return {"success": False, "error": f"Unexpected error: {str(e)}"}


def manage_maintenance_types(
    action: Annotated[
        Literal["list", "get"],
        "The maintenance type operation to perform",
    ],
    maintenance_type_id: Annotated[
        int | None, "Maintenance type ID (required for get action)"
    ] = None,
    limit: Annotated[int | None, "Number of results to return (for list action)"] = 50,
    offset: Annotated[int | None, "Number of results to skip (for list action)"] = 0,
    search: Annotated[str | None, "Search query (for list action)"] = None,
    sort: Annotated[str | None, "Field to sort by (for list action)"] = None,
    order: Annotated[
        Literal["asc", "desc"] | None, "Sort order (for list action)"
    ] = None,
) -> dict[str, Any]:
    """List or fetch maintenance types from Snipe-IT."""
    from server import get_direct_api

    try:
        api = get_direct_api()

        if action == "list":
            params: dict[str, Any] = {"limit": limit or 50, "offset": offset or 0}
            if search:
                params["search"] = search
            if sort:
                params["sort"] = sort
            if order:
                params["order"] = order

            result = api._request("GET", "maintenance-types", params=params)
            rows = result.get("rows", [])
            return {
                "success": True,
                "action": "list",
                "total": result.get("total", len(rows)),
                "count": len(rows),
                "maintenance_types": rows,
            }

        if not maintenance_type_id:
            return {
                "success": False,
                "error": "maintenance_type_id is required for get action",
            }

        result = api._request("GET", f"maintenance-types/{maintenance_type_id}")
        return {
            "success": True,
            "action": "get",
            "maintenance_type": result,
        }

    except SnipeITNotFoundError as e:
        logger.error(f"Resource not found: {e}")
        return {"success": False, "error": f"Not found: {str(e)}"}
    except SnipeITAuthenticationError as e:
        logger.error(f"Authentication error: {e}")
        return {"success": False, "error": f"Authentication failed: {str(e)}"}
    except SnipeITException as e:
        logger.error(f"Snipe-IT error: {e}")
        return {"success": False, "error": f"Snipe-IT error: {str(e)}"}
    except Exception as e:
        logger.exception("Unexpected error in manage_maintenance_types")
        return {"success": False, "error": f"Unexpected error: {str(e)}"}
