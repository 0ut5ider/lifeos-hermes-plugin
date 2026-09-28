# ABOUTME: Exposes the bridge's declared settings to its authenticated dashboard tab.
# ABOUTME: Delegates validation and storage to Hermes's plugin settings service.

from pathlib import Path

from fastapi import APIRouter, HTTPException
from hermes_cli.plugins_settings import plugin_settings_fields, save_plugin_settings


PLUGIN_ID = "lifeos-hook-bridge"
PLUGIN_DIR = Path(__file__).resolve().parents[1]
router = APIRouter()


@router.get("/settings")
def get_settings():
    return {"fields": plugin_settings_fields(PLUGIN_ID, PLUGIN_DIR)}


@router.put("/settings")
def put_settings(values: dict):
    try:
        saved = save_plugin_settings(PLUGIN_ID, PLUGIN_DIR, values)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except PermissionError as error:
        raise HTTPException(status_code=403, detail=str(error)) from error
    return {"saved": saved, "restart_required": bool(saved)}
