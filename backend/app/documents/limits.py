"""Hard ceilings for a single in-memory document inspection."""
MAX_INPUT_BYTES = 8 * 1024 * 1024
MAX_PAGES = 10
MAX_PAGE_CHARS = 30_000
MAX_TOTAL_CHARS = 150_000
MAX_IMAGE_EDGE = 1600
MAX_IMAGE_PIXELS = 2_000_000
MAX_IMAGES_BYTES = 12 * 1024 * 1024
PARSER_TIMEOUT_SECONDS = 12
PARSER_MEMORY_BYTES = 512 * 1024 * 1024


def constrain_process_memory():
    """Fail closed if the OS cannot establish the parser process memory cap."""
    import os
    if os.name != "nt":
        import resource
        resource.setrlimit(resource.RLIMIT_AS, (PARSER_MEMORY_BYTES, PARSER_MEMORY_BYTES))
        return None
    import ctypes as c
    from ctypes import wintypes as w

    class Basic(c.Structure):
        _fields_ = [("PerProcessUserTimeLimit", c.c_int64), ("PerJobUserTimeLimit", c.c_int64),
                    ("LimitFlags", w.DWORD), ("MinimumWorkingSetSize", c.c_size_t),
                    ("MaximumWorkingSetSize", c.c_size_t), ("ActiveProcessLimit", w.DWORD),
                    ("Affinity", c.c_size_t), ("PriorityClass", w.DWORD), ("SchedulingClass", w.DWORD)]

    class IO(c.Structure):
        _fields_ = [(name, c.c_uint64) for name in ("ReadOperationCount", "WriteOperationCount",
                    "OtherOperationCount", "ReadTransferCount", "WriteTransferCount", "OtherTransferCount")]

    class Extended(c.Structure):
        _fields_ = [("BasicLimitInformation", Basic), ("IoInfo", IO), ("ProcessMemoryLimit", c.c_size_t),
                    ("JobMemoryLimit", c.c_size_t), ("PeakProcessMemoryUsed", c.c_size_t),
                    ("PeakJobMemoryUsed", c.c_size_t)]

    kernel = c.WinDLL("kernel32", use_last_error=True)
    kernel.CreateJobObjectW.argtypes = [c.c_void_p, w.LPCWSTR]
    kernel.CreateJobObjectW.restype = w.HANDLE
    kernel.SetInformationJobObject.argtypes = [w.HANDLE, c.c_int, c.c_void_p, w.DWORD]
    kernel.AssignProcessToJobObject.argtypes = [w.HANDLE, w.HANDLE]
    kernel.GetCurrentProcess.restype = w.HANDLE
    job = kernel.CreateJobObjectW(None, None)
    limits = Extended()
    limits.BasicLimitInformation.LimitFlags = 0x100  # JOB_OBJECT_LIMIT_PROCESS_MEMORY
    limits.ProcessMemoryLimit = PARSER_MEMORY_BYTES
    if not job or not kernel.SetInformationJobObject(job, 9, c.byref(limits), c.sizeof(limits)):
        raise RuntimeError("Parser resource boundary unavailable")
    if not kernel.AssignProcessToJobObject(job, kernel.GetCurrentProcess()):
        raise RuntimeError("Parser resource boundary unavailable")
    return job  # Retain handle for the lifetime of this short-lived process.
