# Copyright 2018 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ==============================================================================
"""An integration test that does data generation, training and evaluation."""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import os.path

from absl import flags
from absl.testing import flagsaver
import apache_beam as beam
from pde_superresolution.scripts import create_exact_data
from pde_superresolution.scripts import create_training_data
from pde_superresolution.scripts import run_evaluation
from pde_superresolution.scripts import run_training
import xarray
from absl.testing import absltest


FLAGS = flags.FLAGS


class IntegrationTest(absltest.TestCase):

  def test(self):
    training_path = os.path.join(FLAGS.test_tmpdir, 'training.h5')
    exact_path = os.path.join(FLAGS.test_tmpdir, 'exact.nc')
    checkpoint_dir = os.path.join(FLAGS.test_tmpdir, 'checkpoint')
    samples_output_name = 'results.nc'
    samples_output_path = os.path.join(checkpoint_dir, samples_output_name)

    with flagsaver.flagsaver(
        output_path=training_path,
        equation_name='burgers',
        equation_kwargs='{"num_points": 256}',
        num_tasks=2,
        time_max=1.0,
        time_delta=0.1,
        warmup=0):
      create_training_data.main([], runner=beam.runners.DirectRunner())

    with flagsaver.flagsaver(
        output_path=exact_path,
        equation_name='burgers',
        equation_kwargs='{"num_points": 256}',
        num_samples=2,
        time_max=1.0,
        time_delta=0.1,
        warmup=1.0):
      create_exact_data.main([], runner=beam.runners.DirectRunner())

    with flagsaver.flagsaver(
        checkpoint_dir=checkpoint_dir,
        input_path=training_path,
        hparams='resample_factor=4,learning_rates=[1e-3],learning_stops=[20],'
                'eval_interval=10',
        equation='burgers'):
      run_training.main([])

    with flagsaver.flagsaver(
        checkpoint_dir=checkpoint_dir,
        exact_solution_path=exact_path,
        samples_output_name=samples_output_name,
        num_samples=2,
        time_max=1.0,
        time_delta=0.1):
      run_evaluation.main([], runner=beam.runners.DirectRunner())

    # verify the results
    with xarray.open_dataset(samples_output_path) as ds:
      self.assertEqual(dict(ds.dims),
                       {'sample': 2, 'time': 11, 'x': 64})
      self.assertEqual(set(ds), {'y'})


if __name__ == '__main__':
  absltest.main()
