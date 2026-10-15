# Checkpoint labels do not set retention protection

The 0.5.0 rehearsal, development, and daily pre-update checkpoints exist on Proxmox Backup Server and pass their recorded backup checks. Their native retention metadata nevertheless reports `protected: false`. Naming a receipt field `protected_archive` does not set the storage attribute.

The operator sets `protected=1` through the native Proxmox content endpoint for the three exact archive identifiers. A second native metadata read verifies protection for all three. The change affects retention attributes and preserves archived bytes. The separate safe protection receipt records the correction. Existing release assets and historical checkpoint receipts remain intact.
