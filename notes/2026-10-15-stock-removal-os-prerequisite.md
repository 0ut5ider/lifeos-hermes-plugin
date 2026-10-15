# Stock runtime requires an operating-system library

2026-10-15, disposable Ubuntu 24.04 guest 192.168.8.244.

Installed removal preparation 4d66fcf2c48e42b18ca33afcfc890ac8 passes the initial consumer check and reaches stock runtime assembly. The Node verification command exits 127 because `libatomic.so.1` is missing. The native package manager attempts noninteractive `sudo apt-get install -y libatomic1`, which refuses because the owner account has no passwordless privilege. `dpkg-query` confirms that `libatomic1` is absent. The signed Ubuntu package index provides it as a GCC runtime library.

The ordinary integration path does not stage the complete stock tool set, so its prior successful installation does not establish this prerequisite. The correction is to the disposable operating-system setup and its documented prerequisites. It does not disable stock verification, alter the upstream tool selection, or grant passwordless sudo. The failed preparation leaves built-in Hermes and current memory selected. No removal plan or software publication occurs.

The primary installs `libatomic1` on the disposable guest and repeats normal owner-reviewed preparation. This receipt alone does not establish complete removal acceptance.
