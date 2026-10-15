# Stock provenance requires the complete file set

The initial public-stock validator compares all 18,243 source archive files but ignores extra runtime files. An independent review adds a benign `sitecustomize.py` without changing any archived file. The validator accepts the runtime, and a separate local Python process executes the extra startup module. File equality for known paths does not establish an unmodified runtime.

The primary reproduces that result. Six actual-archive controls show four missing refusals: extra startup source, extra link, extra bytecode, and altered dashboard files. The correction admits only the exact source and dashboard archives, compares their bytes, rejects special files, and requires equality between the admitted and actual runtime file sets. All six controls pass after the correction.

The real public fixture passes the corrected guard with 18,243 source files and 66 dashboard files. The independent closure review also refuses the original startup module, a directory link, and a FIFO. These provenance checks do not claim public installation success. The public replay remains a separate gate after publication.
