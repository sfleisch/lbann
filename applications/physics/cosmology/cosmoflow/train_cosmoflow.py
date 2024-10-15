from typing import Any

import cosmoflow_model

import argparse

import os
import numpy as np

import lbann.contrib.args
import lbann.contrib.launcher
from lbann.core.util import get_parallel_strategy_args
import lbann.util.data
import os
from cosmoflow_dataset import CosmoFlowDataset

def create_python_dataset_reader(args):
    """Create a python dataset reader for CosmoFlow."""

    readers = []
    for role in ['train', 'val', 'test']:
        role_dir = getattr(args, f'{role}_dir')
        if not role_dir:
            continue
        if role == 'val':
            role = 'validate'
        dataset = CosmoFlowDataset(role_dir, args.input_width, args.num_secrets)
        reader = lbann.util.data.construct_python_dataset_reader(dataset, role=role)
        readers.append(reader)

    return lbann.reader_pb2.DataReader(reader=readers)

def create_cosmoflow_data_reader(
        train_path, val_path, test_path, num_responses):
    """Create a data reader for CosmoFlow.

    Args:
        {train, val, test}_path (str): Path to the corresponding dataset.
        num_responses (int): The number of parameters to predict.
    """

    reader_args = []
    if train_path:
        reader_args.append({"role": "train", "data_filename": train_path})
    if val_path and val_path != '__none__':
        reader_args.append({"role": "validate", "data_filename": val_path})
    if test_path and test_path != '__none__':
        reader_args.append({"role": "test", "data_filename": test_path})
    for reader_arg in reader_args:
        reader_arg["data_file_pattern"] = "{}/*.hdf5".format(
            reader_arg["data_filename"])
        reader_arg["hdf5_key_data"] = "full"
        reader_arg["hdf5_key_responses"] = "unitPar"
        reader_arg["num_responses"] = num_responses
        reader_arg.pop("data_filename")

    readers = []
    for reader_arg in reader_args:
        reader = lbann.reader_pb2.Reader(
            name="hdf5",
            shuffle=(reader_arg["role"] != "test"),
            validation_fraction=0,
            absolute_sample_count=0,
            fraction_of_data_to_use=1.0,
            disable_labels=True,
            disable_responses=False,
            scaling_factor_int16=1.0,
            **reader_arg)

        readers.append(reader)

    return lbann.reader_pb2.DataReader(reader=readers)


def create_synthetic_data_reader(input_width: int, num_responses: int) -> Any:
    """Create a synthetic data reader for CosmoFlow.

    Args:
        input_width (int): The size of each input dimension.
        num_responses (int): The number of parameters to predict.
    """
    # Compute how to scale the number of samples from a base of 512^3
    # where smaller sizes are split from that.
    # Conservatively error out otherwise.
    if input_width > 512 or (input_width % 2 != 0):
        raise ValueError(f'Unsupported width {input_width} for synthetic data')
    sample_factor = int((512 // input_width)**3)
    num_samples = {'train': 8010,
                   'validate': 1001,
                   'test': 1001}
    readers = []
    for role in ['train', 'validate', 'test']:
        reader = lbann.reader_pb2.Reader(
            name='synthetic',
            role=role,
            shuffle=(role != 'test'),
            validation_fraction=0,
            fraction_of_data_to_use=1.0,
            absolute_sample_count=0,
            num_samples=num_samples[role]*sample_factor,
            synth_dimensions=f'{num_responses} {input_width} {input_width} {input_width}',
            synth_response_dimensions=str(num_responses)
        )
        readers.append(reader)
    return lbann.reader_pb2.DataReader(reader=readers)


if __name__ == "__main__":
    desc = ('Construct and run the CosmoFlow network on CosmoFlow dataset.'
            'Running the experiment is only supported on LC systems.')
    parser = argparse.ArgumentParser(description=desc)
    lbann.contrib.args.add_scheduler_arguments(parser, 'lbann_cosmoflow')
    lbann.contrib.args.add_profiling_arguments(parser)

    # General arguments
    parser.add_argument(
        '--mini-batch-size', action='store', default=1, type=int,
        help='mini-batch size (default: 1)', metavar='NUM')
    parser.add_argument(
        '--num-epochs', action='store', default=5, type=int,
        help='number of epochs (default: 100)', metavar='NUM')
    parser.add_argument(
        '--random-seed', action='store', default=None, type=int,
        help='the random seed (default: None)')
    parser.add_argument(
        '--dace', action='store_true',
        help='Use the DaCe backend in distconv')

    # Model specific arguments
    parser.add_argument(
        '--input-width', action='store', default=128, type=int,
        help='the input spatial width (default: 128)')
    parser.add_argument(
        '--num-secrets', action='store', default=4, type=int,
        help='number of secrets (default: 4)')
    parser.add_argument(
        '--mlperf', action='store_true',
        help='Use MLPerf HPC compliant model')
    parser.add_argument(
        '--use-batchnorm', action='store_true',
        help='Use batch normalization layers')
    parser.add_argument(
        '--local-batchnorm', action='store_true',
        help='Use local batch normalization mode')
    for role in ['train','val','test']:
        parser.add_argument(f"--{role}-dir", action='store', type=lambda value: None if value == "None" else value
                            default=None, required=(role=='train'),
                            help=f'the directory of the {role} dataset') 
    parser.add_argument(
        '--synthetic', action='store_true',
        help='Use synthetic data')
    parser.add_argument(
        '--python-dataset', action='store_true',
        help='Use python dataset reader')
    parser.add_argument(
        '--no-datastore', action='store_true',
        help='Disable the data store')
    parser.add_argument(
        '--transform-input', action='store_true',
        help='Apply log1p transformation to model inputs')
    parser.add_argument(
        '--dropout-keep-prob', action='store', type=float, default=0.5,
        help='Probability of keeping activations in dropout layers (default: 0.5). Set to 1 to disable dropout')
    parser.add_argument(
        '--cosine-schedule', action='store_true',
        help='Use cosine learning rate scheduler')
    parser.add_argument(
        '--lr-min', action='store', type=float, default=0.,
        help='Minimum leaning rate for cosine scheduler')
    parser.add_argument(
        '--decay-steps', action='store', type=int, default=50000,
        help='Steps to decay learning rate over for cosine scheduler')
    parser.add_argument(
        '--init-warmup-lr', action='store', type=float, default=0.,
        help='Initial warmup learning rate for cosine scheduler')
    parser.add_argument(
        '--warmup-steps', action='store', type=int, default=1000,
        help='Number of steps to warmup learnign rate over with cosine scheduler')

    # Parallelism arguments
    parser.add_argument(
        '--use-distconv', action='store_true',
        help='Enable distconv spatial parallelism.')
    parser.add_argument(
        '--depth-groups', action='store', type=int, default=4,
        help='the k-way partitioning of the depth dimension (default: 4)')
    parser.add_argument(
        '--height-groups', action='store', type=int, default=1,
        help='the k-way partitioning of the height dimension (default: 1)')
    parser.add_argument(
        '--width-groups', action='store', type=int, default=1,
        help='the k-way partitioning of the width dimension (default: 1)')
    parser.add_argument(
        '--channel-groups', action='store', type=int, default=1,
        help='the k-way partitioning of the channel dimension (default: 1)')
    parser.add_argument(
        '--filter-groups', action='store', type=int, default=1,
        help='the k-way partitioning of the filter dimension (default: 1)')
    parser.add_argument(
        '--sample-groups', action='store', type=int, default=1,
        help='the k-way partitioning of the sample dimension (default: 1)')
    parser.add_argument(
        '--min-distconv-width', action='store', type=int, default=None,
        help='the minimum spatial size for which distconv is enabled (default: depth groups)')

    parser.add_argument(
        '--dynamically-reclaim-error-signals', action='store_true',
        help='Allow LBANN to reclaim error signals buffers (default: False)')

    parser.add_argument(
        '--batch-job', action='store_true',
        help='Run as a batch job (default: false)')
    
    parser.add_argument(
        '--work-dir', action='store', type=str, default=None)
    parser.add_argument(
        '--progress', action=argparse.BooleanOptionalAction, default=True,
        help='Display progress bar output (default: true)')

    parser.add_argument('--pbar-newline-interval',
                        type=int,
                        default=100,
                        help='Number of iterations in progress bar before '
                        'printing a newline (default: 100)')

    parser.add_argument('--pbar-width',
                        type=int,
                        default=30,
                        help='Progress bar width, if enabled (default: 30)')

    parser.add_argument('--pbar-moving-avg',
                        type=int,
                        default=10,
                        help='Progress bar iteration time moving average '
                        'length in iterations. Disable moving average with 1 '
                        '(default: 10)')

    parser.add_argument('--pbar-scientific',
                        action='store_true',
                        default=False,
                        help='Use scientific notation for objective value '
                        'printouts in progress bar (default: false)')

    parser.add_argument(
        "--profiler-cmd",
        type=str,
        default=None,
        help="Prefix the lbann command in batch.sh with the specified profiler command. Default no command.")

    parser.add_argument(
        "--pre",
        type=str,
        action="append",
        default=None,
        help="Preamble commands")

    lbann.contrib.args.add_optimizer_arguments(
        parser,
        default_optimizer="momentum",
        default_learning_rate=0.001,
    )
    args = parser.parse_args()

    # Set parallel_strategy
    parallel_strategy = None
    if args.use_distconv:
        if args.mini_batch_size * args.depth_groups < args.nodes * args.procs_per_node:
            print('WARNING the number of samples per mini-batch and depth group (partitions per sample)'
                ' is too small for the number of processes per trainer. Increasing the mini-batch size')
            args.mini_batch_size = int((args.nodes * args.procs_per_node) / args.depth_groups)
            print(f'Increasing mini_batch size to {args.mini_batch_size}')

        parallel_strategy = get_parallel_strategy_args(
            height_groups=args.height_groups,
            width_groups=args.width_groups,
            sample_groups=args.sample_groups,
            channel_groups=args.channel_groups,
            filter_groups=args.filter_groups,
            depth_groups=args.depth_groups)
        
    cosine_scheduler_args = None
    if args.cosine_schedule:
        cosine_scheduler_args = {
            'lr_min': args.lr_min,
            'decay_steps': args.decay_steps,
            'init_warmup_lr': args.init_warmup_lr,
            'warmup_steps': args.warmup_steps
        }

    model = cosmoflow_model.construct_cosmoflow_model(parallel_strategy=parallel_strategy,
                                                      local_batchnorm=args.local_batchnorm,
                                                      input_width=args.input_width,
                                                      num_secrets=args.num_secrets,
                                                      use_batchnorm=args.use_batchnorm,
                                                      num_epochs=args.num_epochs,
                                                      learning_rate=args.optimizer_learning_rate,
                                                      min_distconv_width=args.min_distconv_width,
                                                      mlperf=args.mlperf,
                                                      transform_input=args.transform_input,
                                                      dropout_keep_prob=args.dropout_keep_prob,
                                                      cosine_schedule=cosine_scheduler_args)

    # Print a progress bar
    if args.progress:
        model.callbacks.append(
            lbann.CallbackProgressBar(
                newline_interval=args.pbar_newline_interval,
                print_mem_usage=True,
                moving_average_length=args.pbar_moving_avg,
                bar_width=args.pbar_width,
                scientific_notation=args.pbar_scientific))

    # Add profiling callbacks if needed.
    model.callbacks.extend(lbann.contrib.args.create_profile_callbacks(args))

    # Setup optimizer
    optimizer = lbann.contrib.args.create_optimizer(args)

    # Setup data reader
    serialize_io = False
    if args.synthetic:
        data_reader = create_synthetic_data_reader(
            args.input_width, args.num_secrets)
    elif args.python_dataset:
        data_reader = create_python_dataset_reader(args)
    else:
        data_reader = create_cosmoflow_data_reader(
            args.train_dir,
            args.val_dir,
            args.test_dir,
            num_responses=args.num_secrets)
        serialize_io = True

    # Setup trainer
    random_seed_arg = {'random_seed': args.random_seed} \
        if args.random_seed is not None else {}
    trainer = lbann.Trainer(
        mini_batch_size=args.mini_batch_size,
        serialize_io=serialize_io,
        **random_seed_arg)

    # Runtime parameters/arguments
    environment = lbann.contrib.args.get_distconv_environment(
        num_io_partitions=args.depth_groups if args.use_distconv else 1)
    if args.dynamically_reclaim_error_signals:
        environment['LBANN_KEEP_ERROR_SIGNALS'] = 0
    else:
        environment['LBANN_KEEP_ERROR_SIGNALS'] = 1

    # Setup DaCe kernels if requested
    if args.use_distconv and args.dace:
        environment['DISTCONV_JIT_VERBOSE'] = os.getenv('DISTCONV_JIT_VERBOSE',1)
        application_path=os.path.abspath(os.path.dirname(__file__))
        environment['DISTCONV_JIT_CACHEPATH'] = \
            os.getenv('DISTCONV_JIT_CACHEPATH',f'{application_path}/DaCe_kernels/.dacecache')

    if args.synthetic or args.no_datastore:
        lbann_args = ['--num_io_threads=8']
    else:
        lbann_args = ['--use_data_store']
    lbann_args += lbann.contrib.args.get_profile_args(args)
    profiler_cmd=args.profiler_cmd
    # Was an empty or blank string passed in?
    if profiler_cmd.strip() == '': profiler_cmd=None
    # Remove profiler_cmd from args so that it doesn't get stuck into kwargs.
    del args.profiler_cmd
    if args.pre is not None and len(args.pre)>0:
        preamble_cmds=[c.strip() for c in args.pre if len(c.strip())>0]
        if len(preamble_cmds)==0: preamble_cmds=[]
    else:
        preamble_cmds=[]


    # Run experiment
    kwargs = lbann.contrib.args.get_scheduler_kwargs(args)
    lbann.contrib.launcher.run(
        trainer, model, data_reader, optimizer,
        job_name=args.job_name,
        environment=environment,
        preamble_cmds=preamble_cmds,
        lbann_args=lbann_args,
        batch_job=args.batch_job,
        work_dir=args.work_dir,
        profiler_cmd=profiler_cmd,
        **kwargs)
