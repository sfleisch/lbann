import os
from lbann.contrib.lc.systems import *
import lbann.launcher
from lbann.util import make_iterable

def run(*args, **kwargs):
    """Run LBANN with LC-specific optimizations (deprecated).

    This is deprecated. Use `lbann.contrib.launcher.run` instead.

    """

    import warnings
    warnings.warn(
        'Using deprecated function `lbann.contrib.lc.launcher.run`. '
        'Use `lbann.contrib.launcher.run` instead.'
    )
    from ..launcher import run as _run
    _run(*args, **kwargs)

def make_batch_script(
    system=system(),
    procs_per_node=procs_per_node(),
    scheduler=scheduler(),
    launcher_args=[],
    environment={},
    *args,
    **kwargs,
):
    """Construct batch script manager with LC-specific optimizations.

    This is a wrapper around `lbann.launcher.make_batch_script`, with
    defaults and optimizations for LC systems. See that function for a
    full list of options.

    """

    # Create shallow copies of input arguments
    launcher_args = list(make_iterable(launcher_args))
    environment = environment.copy()

    # Helper function to configure environment variables
    # Note: User-provided values take precedence, followed by values
    # in the environment, followed by default values.
    def set_environment(key, default):
        if key not in environment:
            environment[key] = os.getenv(key, default)

    def prepend_environment_path(key, prefix):
        if key not in environment:
            environment[key] = prefix + ":" + os.getenv(key)
        else:
            environment[key] = prefix + ":" + environment[key]

    # Setup GPU bindings
    # Note: Each Hydrogen process is assigned to the GPU index that
    # matches its node communicator rank. This is not compatible with
    # mpibind, which assigns a GPU with index 0 to each process. We
    # can't use an exclusive GPU compute mode since processes may
    # touch the wrong GPU while figuring out ownership.
    if scheduler == 'slurm' and has_gpu(system):
        launcher_args.extend(['--mpibind=off'])

    # if scheduler == 'flux' and system == 'corona':
        # If using mvapich2 use PMI2
        # launcher_args.extend(['-o pmi=pmi2'])
        # if usuing OpenMPI use PMIx
        # launcher_args.extend(['-o pmi=pmix'])

    # Optimized thread affinity for Pascal
    # Note: Both GPUs are on socket 0, so we only use cores on that
    # socket.
    if system == 'pascal':
        cores_per_socket = cores_per_node(system) // 2
        cores_per_proc = cores_per_socket // procs_per_node
        set_environment('AL_PROGRESS_RANKS_PER_NUMA_NODE', procs_per_node)
        if scheduler == 'slurm':
            # Include the hyperthreaded cores in the mask
            masks = [2**cores_per_proc - 1 | ((2**cores_per_proc - 1) << 2*cores_per_socket)]
            while len(masks) < procs_per_node:
                masks.append(masks[-1] << cores_per_proc)
            mask_str = ','.join([hex(mask) for mask in masks])
            launcher_args.append('--cpu_bind=mask_cpu:{}'.format(mask_str))

    # Hacked bugfix for MPI_Init in MVAPICH2-2.3 (8/23/18)
    # Note: MPI_Init hangs when started with more than 35
    # processes. This bug is not present in MVAPICH2-2.2 but is
    # present in MVAPICH2-2.3rc2.
    set_environment('MV2_USE_RDMA_CM', 0)

    # Bugfix for pascal as of 9/21/22
    # set_environment('MV2_USE_ALIGNED_ALLOC', 1) # Not necessary because we don't allocate from multiple threads
    set_environment('MV2_HOMOGENEOUS_CLUSTER', 1)
    set_environment('MV2_USE_THREAD_WARNING', 0)

    # Optimizations for Tioga
    if system in ('tioga', 'rzvernal', 'elcap', 'tuolumne', 'rzadams'):
        #set_environment('NCCL_SOCKET_IFNAME', 'hsi')
        set_environment('NCCL_NET_GDR_LEVEL', '3') # From HPE to avoid hangs
        set_environment('MIOPEN_DEBUG_DISABLE_FIND_DB', '0')
        set_environment('MIOPEN_DISABLE_CACHE', '0')
        tmpdir = os.environ.get('TMPDIR')
        set_environment('MIOPEN_USER_DB_PATH', f'{tmpdir}/MIOpen_user_db')
        set_environment('MIOPEN_CUSTOM_CACHE_DIR', f'{tmpdir}/MIOpen_custom_cache')
        if os.getenv('CRAY_LD_LIBRARY_PATH') is not None:
            prepend_environment_path('LD_LIBRARY_PATH', os.getenv('CRAY_LD_LIBRARY_PATH'))
        if os.getenv('ROCM_PATH') is not None:
            prepend_environment_path('LD_LIBRARY_PATH', os.path.join(os.getenv('ROCM_PATH'), 'llvm', 'lib'))
        different_ofi_plugin = os.getenv('LBANN_USE_THIS_OFI_PLUGIN')
        if different_ofi_plugin is not None:
            prepend_environment_path('LD_LIBRARY_PATH', different_ofi_plugin)

    # Optimizations for Corona
    if system in ('corona'):
        # Hack to enable process forking
        # Note: InfiniBand is known to experience hangs if an MPI
        # process is forked (see
        # https://www.open-mpi.org/faq/?category=openfabrics#ofa-fork).
        # Setting IBV_FORK_SAFE seems to fix this issue, but it may
        # hurt performance (see
        # https://linux.die.net/man/3/ibv_fork_init).
        set_environment('IBV_FORK_SAFE', 1)
        # If you are *absolutely sure* that your application will successfully
        # and correctly survive a call to fork(), you may disable this warning
        # by setting the mpi_warn_on_fork MCA parameter to 0.
        set_environment('OMPI_MCA_mpi_warn_on_fork', 0)

        #set_environment('NCCL_SOCKET_IFNAME', 'hsi')
        set_environment('MIOPEN_DEBUG_DISABLE_FIND_DB', '0')
        set_environment('MIOPEN_DISABLE_CACHE', '0')
        tmpdir = os.environ.get('TMPDIR')
        set_environment('MIOPEN_USER_DB_PATH', f'{tmpdir}/MIOpen_user_db')
        set_environment('MIOPEN_CUSTOM_CACHE_DIR', f'{tmpdir}/MIOpen_custom_cache')
        if os.getenv('ROCM_PATH') is not None:
            prepend_environment_path('LD_LIBRARY_PATH', os.path.join(os.getenv('ROCM_PATH'), 'llvm', 'lib'))
        # Ensure that the correct PMI is set to avoid hangs, etc.
        launcher_args.append('-o pmi=pmix')

    # Optimizations for Sierra-like systems
    if system in ('sierra', 'lassen', 'rzansel'):

        # Set thread affinity
        # Note: Aluminum's default thread affinity is incorrect since
        # hwloc treats GPUs as NUMA domains.
        # Note: There are actually 22 cores/socket, but it seems that
        # powers of 2 are better for performance.
        cores_per_socket = 16
        procs_per_socket = (procs_per_node + 1) // 2
        cores_per_proc = cores_per_socket // procs_per_socket
        set_environment('AL_PROGRESS_RANKS_PER_NUMA_NODE', procs_per_socket)
        if scheduler == 'lsf':
            launcher_args.append('--bind packed:{}'.format(cores_per_proc))
            launcher_args.append('--smpiargs="-gpu"')

        # Hack to enable process forking
        # Note: InfiniBand is known to experience hangs if an MPI
        # process is forked (see
        # https://www.open-mpi.org/faq/?category=openfabrics#ofa-fork).
        # Setting IBV_FORK_SAFE seems to fix this issue, but it may
        # hurt performance (see
        # https://linux.die.net/man/3/ibv_fork_init).
        set_environment('IBV_FORK_SAFE', 1)

        # Hacked bugfix for hcoll (1/23/19)
        # Note: Fixes hangs in MPI_Bcast.
        set_environment('HCOLL_ENABLE_SHARP', 0)
        set_environment('OMPI_MCA_coll_hcoll_enable', 0)

        # Hacked bugfix for Spectrum MPI PAMI (9/17/19)
        set_environment('PAMI_MAX_NUM_CACHED_PAGES', 0)

        # Configure NVSHMEM to load Spectrum MPI
        set_environment('NVSHMEM_MPI_LIB_NAME', 'libmpi_ibm.so')



    return lbann.launcher.make_batch_script(
        procs_per_node=procs_per_node,
        scheduler=scheduler,
        launcher_args=launcher_args,
        environment=environment,
        *args,
        **kwargs,
    )
