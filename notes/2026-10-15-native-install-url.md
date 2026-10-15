# 2026-10-15: Preserve the manager subdirectory in the native install URL

The fresh release operator enters the bare repository URL in the actual stock Hermes Plugins form. The native installer checks out the repository root into its temporary plugin folder. That root has no plugin.yaml. The documented install URL includes .git#optional/lifeos_release_manager. The earlier wording "default GitHub URL" does not identify that required subdirectory.

The first attempt remains unqualified. The operator does not wait for a final installer result and does not claim that Hermes rejects every bare repository. It stops only the owned CT112 and restores its pristine pre-install snapshot. The snapshot has no LifeOS personal store, import, or memory policy. The corrected test uses the documented full URL. Development and daily are unchanged. The main README now names the documented install URL explicitly.
