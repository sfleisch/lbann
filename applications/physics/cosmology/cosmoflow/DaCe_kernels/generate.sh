#!/bin/sh
source $LMOD_PKG/init/sh
export CC=`which amdclang`
export CXX=`which amdclang++`
export DACE_compiler_extra_cmake_args="-DHIP_CLANG_PATH=${ROCM_PATH}/llvm/bin"
export DACE_CONFIG=$(realpath $(dirname "$0"))/dace.conf
export LIBRARY_PATH=$LIBRARY_PATH:$ROCM_PATH/lib
export WSPSIZE=2048
export CPATH=$CPATH:${ROCM_PATH}/include/rocblas
CLUSTER=$(hostname | sed 's/[0-9]*//g')
case "${CLUSTER}" in
    rzvernal|tioga)
        DACE_compiler_cuda_hip_arch=gfx90a
        ;;
    corona)
        DACE_compiler_cuda_hip_arch=gfx906
        ;;
    tuolumne|elcap|rzadams)
        DACE_compiler_cuda_hip_arch=gfx942
        ;;
    *)
        ;;
esac

generate_conv3d_fwd() {
    # Explicit GEMM
    python3 generate_egemm_fwd.py explicit $WSPSIZE conv $*
}

generate_conv3d_bwddata() {
    # Explicit GEMM
    python3 generate_egemm_bwddata.py explicit $WSPSIZE conv $*
}

generate_conv3d_bwdfilt() {
    # Explicit GEMM
    python3 generate_egemm_bwdfilter.py explicit $WSPSIZE conv $*
}

#B="-1"
#B=2

for B in 1 2;do
# 512 MLPerf + distconv + depth-groups=8
generate_conv3d_fwd $B 4 66 512 512 69206016 17301504 262144 512 1 32 4 3 3 3 $B 32 64 512 512 553648128 17301504 262144 512 1 0 1 1 1 1 1 1 1 1 1 fwd
generate_conv3d_fwd $B 32 34 256 256 71303168 2228224 65536 256 1 64 32 3 3 3 $B 64 32 256 256 142606336 2228224 65536 256 1 0 1 1 1 1 1 1 1 1 1 fwd
generate_conv3d_fwd $B 64 18 128 128 18874368 294912 16384 128 1 128 64 3 3 3 $B 128 16 128 128 37748736 294912 16384 128 1 0 1 1 1 1 1 1 1 1 1 fwd
################################################################################
# These kernels are currently faster in vendor library
# generate_conv3d_fwd $B 128 10 64 64 5242880 40960 4096 64 1 256 128 3 3 3 $B 256 8 64 64 10485760 40960 4096 64 1 0 1 1 1 1 1 1 1 1 1 fwd
# generate_conv3d_fwd $B 256 6 32 32 1572864 6144 1024 32 1 512 256 3 3 3 $B 512 4 32 32 3145728 6144 1024 32 1 0 1 1 1 1 1 1 1 1 1 fwd
# generate_conv3d_fwd $B 512 4 16 16 524288 1024 256 16 1 512 512 3 3 3 $B 512 2 16 16 524288 1024 256 16 1 0 1 1 1 1 1 1 1 1 1 fwd
# generate_conv3d_fwd $B 512 3 8 8 98304 192 64 8 1 512 512 3 3 3 $B 512 1 8 8 98304 192 64 8 1 0 1 1 1 1 1 1 1 1 1 fwd
# generate_conv3d_bwdfilt $B 512 3 8 8 98304 192 64 8 1 512 512 3 3 3 $B 512 3 8 8 98304 192 64 8 1 1 1 1 1 1 1 1 1 1 1 bwdfilt
# generate_conv3d_bwddata $B 512 3 8 8 98304 192 64 8 1 512 512 3 3 3 $B 512 3 8 8 98304 192 64 8 1 1 1 1 1 1 1 1 1 1 1 bwddata
# generate_conv3d_bwdfilt $B 512 4 16 16 524288 1024 256 16 1 512 512 3 3 3 $B 512 4 16 16 524288 1024 256 16 1 1 1 1 1 1 1 1 1 1 1 bwdfilt
# generate_conv3d_bwddata $B 512 4 16 16 524288 1024 256 16 1 512 512 3 3 3 $B 512 4 16 16 524288 1024 256 16 1 1 1 1 1 1 1 1 1 1 1 bwddata
# generate_conv3d_bwdfilt $B 256 6 32 32 1572864 6144 1024 32 1 512 256 3 3 3 $B 512 6 32 32 3145728 6144 1024 32 1 1 1 1 1 1 1 1 1 1 1 bwdfilt
# generate_conv3d_bwddata $B 256 6 32 32 1572864 6144 1024 32 1 512 256 3 3 3 $B 512 6 32 32 3145728 6144 1024 32 1 1 1 1 1 1 1 1 1 1 1 bwddata
# generate_conv3d_bwdfilt $B 128 10 64 64 5242880 40960 4096 64 1 256 128 3 3 3 $B 256 10 64 64 10485760 40960 4096 64 1 1 1 1 1 1 1 1 1 1 1 bwdfilt
# generate_conv3d_bwddata $B 128 10 64 64 5242880 40960 4096 64 1 256 128 3 3 3 $B 256 10 64 64 10485760 40960 4096 64 1 1 1 1 1 1 1 1 1 1 1 bwddata
################################################################################
generate_conv3d_bwdfilt $B 64 18 128 128 18874368 294912 16384 128 1 128 64 3 3 3 $B 128 18 128 128 37748736 294912 16384 128 1 1 1 1 1 1 1 1 1 1 1 bwdfilt
generate_conv3d_bwddata $B 64 18 128 128 18874368 294912 16384 128 1 128 64 3 3 3 $B 128 18 128 128 37748736 294912 16384 128 1 1 1 1 1 1 1 1 1 1 1 bwddata
generate_conv3d_bwdfilt $B 32 34 256 256 71303168 2228224 65536 256 1 64 32 3 3 3 $B 64 34 256 256 142606336 2228224 65536 256 1 1 1 1 1 1 1 1 1 1 1 bwdfilt
generate_conv3d_bwddata $B 32 34 256 256 71303168 2228224 65536 256 1 64 32 3 3 3 $B 64 34 256 256 142606336 2228224 65536 256 1 1 1 1 1 1 1 1 1 1 1 bwddata
generate_conv3d_bwdfilt $B 4 66 512 512 69206016 17301504 262144 512 1 32 4 3 3 3 $B 32 66 512 512 553648128 17301504 262144 512 1 1 1 1 1 1 1 1 1 1 1 bwdfilt
generate_conv3d_bwddata $B 4 66 512 512 69206016 17301504 262144 512 1 32 4 3 3 3 $B 32 66 512 512 553648128 17301504 262144 512 1 1 1 1 1 1 1 1 1 1 1 bwddata

# 512 MLPerf + distconv + depth-groups=4
generate_conv3d_fwd $B 4 130 512 512 136314880 34078720 262144 512 1 32 4 3 3 3 $B 32 128 512 512 1090519040 34078720 262144 512 1 0 1 1 1 1 1 1 1 1 1 fwd
generate_conv3d_fwd $B 32 66 256 256 138412032 4325376 65536 256 1 64 32 3 3 3 $B 64 64 256 256 276824064 4325376 65536 256 1 0 1 1 1 1 1 1 1 1 1 fwd
generate_conv3d_fwd $B 64 34 128 128 35651584 557056 16384 128 1 128 64 3 3 3 $B 128 32 128 128 71303168 557056 16384 128 1 0 1 1 1 1 1 1 1 1 1 fwd
################################################################################
# These kernels are currently faster in vendor library
# generate_conv3d_fwd $B 128 18 64 64 9437184 73728 4096 64 1 256 128 3 3 3 $B 256 16 64 64 18874368 73728 4096 64 1 0 1 1 1 1 1 1 1 1 1 fwd
# generate_conv3d_fwd $B 256 10 32 32 2621440 10240 1024 32 1 512 256 3 3 3 $B 512 8 32 32 5242880 10240 1024 32 1 0 1 1 1 1 1 1 1 1 1 fwd
# generate_conv3d_fwd $B 512 6 16 16 786432 1536 256 16 1 512 512 3 3 3 $B 512 4 16 16 786432 1536 256 16 1 0 1 1 1 1 1 1 1 1 1 fwd
# generate_conv3d_fwd $B 512 4 8 8 131072 256 64 8 1 512 512 3 3 3 $B 512 2 8 8 131072 256 64 8 1 0 1 1 1 1 1 1 1 1 1 fwd
# generate_conv3d_bwdfilt $B 512 4 8 8 131072 256 64 8 1 512 512 3 3 3 $B 512 4 8 8 131072 256 64 8 1 1 1 1 1 1 1 1 1 1 1 bwdfilt
# generate_conv3d_bwddata $B 512 4 8 8 131072 256 64 8 1 512 512 3 3 3 $B 512 4 8 8 131072 256 64 8 1 1 1 1 1 1 1 1 1 1 1 bwddata
# generate_conv3d_bwdfilt $B 512 6 16 16 786432 1536 256 16 1 512 512 3 3 3 $B 512 6 16 16 786432 1536 256 16 1 1 1 1 1 1 1 1 1 1 1 bwdfilt
# generate_conv3d_bwddata $B 512 6 16 16 786432 1536 256 16 1 512 512 3 3 3 $B 512 6 16 16 786432 1536 256 16 1 1 1 1 1 1 1 1 1 1 1 bwddata
# generate_conv3d_bwdfilt $B 256 10 32 32 2621440 10240 1024 32 1 512 256 3 3 3 $B 512 10 32 32 5242880 10240 1024 32 1 1 1 1 1 1 1 1 1 1 1 bwdfilt
# generate_conv3d_bwddata $B 256 10 32 32 2621440 10240 1024 32 1 512 256 3 3 3 $B 512 10 32 32 5242880 10240 1024 32 1 1 1 1 1 1 1 1 1 1 1 bwddata
# generate_conv3d_bwdfilt $B 128 18 64 64 9437184 73728 4096 64 1 256 128 3 3 3 $B 256 18 64 64 18874368 73728 4096 64 1 1 1 1 1 1 1 1 1 1 1 bwdfilt
# generate_conv3d_bwddata $B 128 18 64 64 9437184 73728 4096 64 1 256 128 3 3 3 $B 256 18 64 64 18874368 73728 4096 64 1 1 1 1 1 1 1 1 1 1 1 bwddata
################################################################################
generate_conv3d_bwdfilt $B 64 34 128 128 35651584 557056 16384 128 1 128 64 3 3 3 $B 128 34 128 128 71303168 557056 16384 128 1 1 1 1 1 1 1 1 1 1 1 bwdfilt
generate_conv3d_bwddata $B 64 34 128 128 35651584 557056 16384 128 1 128 64 3 3 3 $B 128 34 128 128 71303168 557056 16384 128 1 1 1 1 1 1 1 1 1 1 1 bwddata
generate_conv3d_bwdfilt $B 32 66 256 256 138412032 4325376 65536 256 1 64 32 3 3 3 $B 64 66 256 256 276824064 4325376 65536 256 1 1 1 1 1 1 1 1 1 1 1 bwdfilt
generate_conv3d_bwddata $B 32 66 256 256 138412032 4325376 65536 256 1 64 32 3 3 3 $B 64 66 256 256 276824064 4325376 65536 256 1 1 1 1 1 1 1 1 1 1 1 bwddata
generate_conv3d_bwdfilt $B 4 130 512 512 136314880 34078720 262144 512 1 32 4 3 3 3 $B 32 130 512 512 1090519040 34078720 262144 512 1 1 1 1 1 1 1 1 1 1 1 bwdfilt
generate_conv3d_bwddata $B 4 130 512 512 136314880 34078720 262144 512 1 32 4 3 3 3 $B 32 130 512 512 1090519040 34078720 262144 512 1 1 1 1 1 1 1 1 1 1 1 bwddata
done
exit 0
