# Version restore and external user data

Date: 2026-10-02.

The failed browser restore reports two changed paths. Both resolve to the same configuration audit file. The live aliases have inode 221526129 and reference a 321,501-byte file in the isolated acceptance USER directory. The initial idea was to copy later audit bytes into the prior program snapshot. That would add publication and recovery states for data that never moves during the program swap.

LifeOS installs USER and MEMORY as links into an external owner directory. The transaction now binds those links to their resolved directory, device, and inode. Restore checks both program trees against that record. External facts, retirement state, and audit entries stay in place. Embedded user data retains the strict digest guard because a program swap would replace it.

The failing tests reproduce the audit refusal and show that matching bytes alone cannot detect a replaced external link or directory. The corrected 15-case transaction test verifies current facts, deleted facts, audit preservation, alias replacement refusal, embedded-data refusal, and profile archive recovery. Live browser verification follows in the readiness record.
