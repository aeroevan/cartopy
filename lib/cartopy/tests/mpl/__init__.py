# (C) British Crown Copyright 2011 - 2012, Met Office
#
# This file is part of cartopy.
#
# cartopy is free software: you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by the
# Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# cartopy is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with cartopy.  If not, see <http://www.gnu.org/licenses/>.


import os
import shutil
import warnings


import matplotlib.testing.compare as mcompare
import matplotlib._pylab_helpers as pyplot_helpers


class ImageTesting(object):
    """
    Provides a convenient class for running visual matplotlib tests.

    In general, this class should be used as a decorator to a test function
    which generates one (or more) figures.

    ::

        @ImageTesting(['simple_test'])
        def test_simple():

            import matplotlib.pyplot as plt
            plt.plot(range(10))

    """

    root_image_results = os.path.dirname(__file__)
    """
    The path where the standard ``baseline_images`` and
    ``img_test_output`` directories go.

    """

    def __init__(self, img_names, tolerance=1e-3):
        self.img_names = img_names
        self.tolerance = tolerance

    def expected_path(self, test_name, img_name):
        """
        Return the full path (minus extension) of where the expected image
        should be found, given the name of the image being tested and the
        name of the test being run.

        """
        expected_fname = os.path.join(self.root_image_results,
                                      'baseline_images', 'mpl', test_name,
                                      img_name)
        return expected_fname

    def result_path(self, test_name, img_name):
        """
        Return the full path (minus extension) of where the result image
        should be given the name of the image being tested and the
        name of the test being run.

        """
        result_fname = os.path.join(self.root_image_results,
                                    'output', test_name,
                                    'result-' + img_name)
        return result_fname

    def run_figure_comparisons(self, figures, test_name):
        """
        Run the figure comparisons against the ``image_names``.

        The number of figures passed must be equal to the number of
        image names in ``self.image_names``.

        .. note::

            The figures are not closed by this method. If using the decorator
            version of ImageTesting, they will be closed for you.

        """
        n_figures_msg = ('Expected %s figures (based  on the number of image '
                         'result filenames), but there are %s figures available. '
                         'The most likely reason for this is that this test is producing '
                         'too many figures, (alternatively if not using ImageCompare as a '
                         'decorator, it is possible that a test run prior to this one has not '
                         'closed its figures).' % (len(self.img_names), len(figures))
                         )
        assert len(figures) == len(self.img_names), n_figures_msg

        for img_name, figure in zip(self.img_names, figures):
            expected_path = self.expected_path(test_name, img_name)
            result_path = self.result_path(test_name, img_name)

            # add the extension to the paths:
            result_path += '.png'
            expected_path += '.png'

            if not os.path.isdir(os.path.dirname(expected_path)):
                os.makedirs(os.path.dirname(expected_path))

            if not os.path.isdir(os.path.dirname(result_path)):
                os.makedirs(os.path.dirname(result_path))

            self.save_figure(figure, result_path)

            self.do_compare(result_path, expected_path, self.tolerance)

    def save_figure(self, figure, result_fname):
        """
        The actual call which saves the figure.

        Returns nothing.

        May be overridden to do figure based pre-processing (such
        as removing text objects etc.)
        """
        figure.savefig(result_fname)

    def do_compare(self, result_fname, expected_fname, tol):
        """
        Runs the comparison of the result file with the expected file.

        If an RMS difference greater than ``tol`` is found an assertion
        error is raised with an appropriate message with the paths to
        the files concerned.

        """
        if not os.path.exists(expected_fname):
            warnings.warn('Created image in %s' % expected_fname)
            shutil.copy2(result_fname, expected_fname)

        err = mcompare.compare_images(expected_fname, result_fname, tol=tol, in_decorator=True)

        if err:
            msg = ('Images were different (RMS: %s).\n%s %s %s\nConsider running idiff to '
                   'inspect these differences.' % (err['rms'], err['actual'],
                                                   err['expected'], err['diff']))
            assert False, msg

    def __call__(self, test_func):
        """Called when the decorator is applied to a function."""
        test_name = test_func.__name__
        mod_name = test_func.__module__
        if mod_name == '__main__':
            import sys
            fname = sys.modules[mod_name].__file__
            mod_name = os.path.basename(os.path.splitext(fname)[0])
        mod_name = mod_name.rsplit('.', 1)[-1]

        def wrapped(*args, **kwargs):
            if pyplot_helpers.Gcf.figs:
                warnings.warn('Figures existed before running the %s %s test. All figures should be '
                              'closed after they run. They will be closed automatically now.' %
                              (mod_name, test_name))
                fig_managers = pyplot_helpers.Gcf.destroy_all()


            r = test_func(*args, **kwargs)

            fig_managers = pyplot_helpers.Gcf._activeQue
            figures = [manager.canvas.figure for manager in fig_managers]

            try:
                self.run_figure_comparisons(figures, test_name=mod_name)
            finally:
                for figure in figures:
                    pyplot_helpers.Gcf.destroy_fig(figure)

        # nose needs the function's name to be in the form "test_*" to pick it up
        wrapped.__name__ = test_name
        return wrapped