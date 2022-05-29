#
#  Copyright (C) 2016, 2018, 2020, 2021, 2022
#  Smithsonian Astrophysical Observatory
#
#
#  This program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 3 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License along
#  with this program; if not, write to the Free Software Foundation, Inc.,
#  51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
#

from io import StringIO
import os

import numpy

import pytest

from sherpa.astro.data import DataPHA
from sherpa.astro.instrument import create_arf
from sherpa.astro.ui.utils import Session as AstroSession
from sherpa.data import Data1D, Data1DInt
from sherpa.io import get_ascii_data
from sherpa.models import Const1D
import sherpa.models.basic
from sherpa.ui.utils import Session
from sherpa.utils.err import ArgumentErr, ArgumentTypeErr, DataErr, IdentifierErr
from sherpa.utils.testing import requires_data, requires_fits, requires_group


# bug #303
def test_show_bkg_model():
    session = AstroSession()
    session.load_arrays(1, [1, 2], [1, 2])
    session.show_bkg_model()
    session.show_bkg_model('xx')
    session.show_bkg_source()
    session.show_bkg_source('xx')


# bug #303
@requires_data
@requires_fits
def test_show_bkg_model_with_bkg(make_data_path):
    session = AstroSession()
    session.load_data('foo', make_data_path('3c273.pi'))
    session.show_bkg_model()
    session.show_bkg_model('foo')


# Fix 476 - this should be in sherpa/ui/tests/test_session.py
@requires_group
def test_zero_division_calc_stat():
    ui = AstroSession()
    x = numpy.arange(100)
    y = numpy.zeros(100)
    ui.load_arrays(1, x, y, DataPHA)
    ui.group_counts(1, 100)
    ui.set_full_model(1, Const1D("const"))

    # in principle I wouldn't need to call calc_stat_info(), I could just
    # use _get_stat_info to reproduce the issue, However, _get_stat_info is not a public
    # method, so I want to double check that calc_stat_info does not throw an exception.
    # So, first we try to run calc_stat_info and make sure there are no exceptions.
    # Then, since calc_stat_info only logs something and doesn't return anything, we use
    # a white box approach to get the result from _get_stat_info.
    ui.calc_stat_info()
    assert ui._get_stat_info()[0].rstat is numpy.nan


@pytest.mark.parametrize("session", [Session, AstroSession])
def test_get_iter_method_name_default(session):
    s = Session()
    assert s.get_iter_method_name() == "none"


@pytest.mark.parametrize("session", [Session, AstroSession])
@pytest.mark.parametrize("opt", ["none", "sigmarej"])
def test_set_iter_method_valid(session, opt):
    s = Session()
    s.set_iter_method(opt)
    assert s.get_iter_method_name() == opt


@pytest.mark.parametrize("session", [Session, AstroSession])
def test_set_iter_method_unknown_string(session):
    s = Session()
    with pytest.raises(TypeError,
                       match="^not a method is not an iterative fitting method$"):
        s.set_iter_method("not a method")


@pytest.mark.parametrize("session", [Session, AstroSession])
def test_set_iter_method_not_a_string(session):
    s = Session()
    with pytest.raises(ArgumentTypeErr,
                       match="^'meth' must be a string$"):
        s.set_iter_method(23)


@pytest.mark.parametrize("session", [Session, AstroSession])
def test_get_iter_method_opt_default(session):
    s = Session()
    assert s.get_iter_method_opt() == {}


@pytest.mark.parametrize("session", [Session, AstroSession])
def test_get_iter_method_opt_sigmarej(session):
    s = Session()
    s.set_iter_method("sigmarej")
    out = s.get_iter_method_opt()

    keys = set(out.keys())
    assert keys == set(["grow", "lrej", "hrej", "maxiters"])


@pytest.mark.parametrize("session", [Session, AstroSession])
def test_get_iter_method_opt_sigmarej_lrej(session):
    s = Session()
    s.set_iter_method("sigmarej")
    assert s.get_iter_method_opt("lrej") == pytest.approx(3)


@pytest.mark.parametrize("session", [Session, AstroSession])
@pytest.mark.parametrize("opt,key", [("none", "lrej"), ("sigmarej", "fast")])
def test_get_iter_method_opt_unknown(session, opt, key):
    s = Session()
    s.set_iter_method(opt)
    with pytest.raises(ArgumentErr,
                       match=f"^'{key}' is not a valid option for method {opt}$"):
        s.get_iter_method_opt(key)


@pytest.mark.parametrize("session", [Session, AstroSession])
def test_set_iter_method_opt_sigmarej_lrej(session):
    s = Session()
    s.set_iter_method("sigmarej")
    s.set_iter_method_opt("lrej", 5)
    assert s.get_iter_method_opt("lrej") == pytest.approx(5)


@pytest.mark.parametrize("session", [Session, AstroSession])
@pytest.mark.parametrize("setting", ['chisqr', 'compmodel', 'compsource', 'data',
                                     'delchi', 'fit', 'kernel', 'model',
                                     'psf', 'ratio', 'resid', 'source'])
def test_id_checks_session(session, setting):
    """Do some common identifiers fail?"""

    s = session()
    with pytest.raises(IdentifierErr,
                       match=f"identifier '{setting}' is a reserved word"):
        s.load_arrays(setting, [1, 2], [1, 2])


@pytest.mark.parametrize("session", [Session, AstroSession])
@pytest.mark.parametrize("setting", ['cdf', 'energy', 'lr', 'photon', 'pdf', 'scatter', 'trace',
                                     "bkg_model", "bkg_source", "bkg_resid", "bkg_ratio",
                                     "bkg_delchi", "bkg_chisqr", "bkg_fit"
                                     ])
def test_id_checks_session_unexpected(session, setting):
    """These identifiers are allowed. Should they be?"""

    s = session()
    s.load_arrays(setting, [1, 2], [1, 2])
    d = s.get_data(setting)
    assert isinstance(d, Data1D)


@pytest.mark.parametrize("session,success",
                         [(Session, True), (AstroSession, False)])
@pytest.mark.parametrize("setting", ['arf', 'bkg', 'bkgchisqr', 'bkgdelchi', 'bkgfit',
                                     'bkgmodel', 'bkgratio', 'bkgresid', 'bkgsource',
                                     'order',
                                     # "energy", "photon",  these are currently both valid for astro
                                     "astrocompsource", "astrocompmodel", "astrodata",
                                     "astrosource", "astromodel"])
def test_id_checks_astro_session(session, success, setting):
    """Do some common identifiers fail for astro but not default?"""

    s = session()
    if success:
        s.load_arrays(setting, [1, 2], [1, 2])
        d = s.get_data(setting)
        assert isinstance(d, Data1D)
    else:
        with pytest.raises(IdentifierErr,
                           match=f"identifier '{setting}' is a reserved word"):
            s.load_arrays(setting, [1, 2], [1, 2])


def save_ascii_file(s, kwargs, idval, outfile, savefunc, syserr=False):
    """create data and save a file based on it"""

    s._add_model_types(sherpa.models.basic)

    cpt = s.create_model_component("const1d", "cpt")
    cpt.integrate = True
    cpt.c0 = 2

    # Select bin edges that lead to integer for the middle values,
    # along with the model per-bin values (2 * width).
    #
    s.load_arrays(idval, [1, 3, 5], [3, 5, 9], [3, 4, 5], Data1DInt)
    dy = [1, 2, 6]

    errfunc = s.set_syserror if syserr else s.set_staterror

    if idval is None:
        errfunc(dy)
        s.set_source(cpt)
        savefunc(str(outfile), **kwargs)
    else:
        errfunc(idval, dy)
        s.set_staterror(idval, dy)
        s.set_source(idval, cpt)
        savefunc(idval, str(outfile), **kwargs)


def get_data(path, **kwargs):
    """wrapper routine to handle path conversion and dropping last argument."""

    ans = get_ascii_data(str(path), **kwargs)
    return ans[0], ans[1]


@requires_fits  # only for AstroSession, but not worth being clever
@pytest.mark.parametrize("session,kwargs",
                         [(Session, {}), (AstroSession, {"ascii": True})])
@pytest.mark.parametrize("idval", [None, 1, "bob"])
def test_save_model_ascii(session, kwargs, idval, tmp_path):
    """Can we use save_model?"""

    s = session()
    outfile = tmp_path / "model.dat"
    save_ascii_file(s, kwargs, idval, outfile, s.save_model)

    names, data = get_data(outfile, ncols=2)
    assert names == ["X", "MODEL"]
    assert len(data) == 2
    assert data[0] == pytest.approx([2, 4, 7])
    assert data[1] == pytest.approx([4, 4, 8])


@requires_fits  # only for AstroSession, but not worth being clever
@pytest.mark.parametrize("session,kwargs",
                         [(Session, {}), (AstroSession, {"ascii": True})])
@pytest.mark.parametrize("idval", [None, 1, "bob"])
def test_save_source_ascii(session, kwargs, idval, tmp_path):
    """Can we use save_source?"""

    s = session()
    outfile = tmp_path / "source.dat"
    save_ascii_file(s, kwargs, idval, outfile, s.save_source)

    names, data = get_data(outfile, ncols=2)
    assert names == ["X", "SOURCE"]
    assert len(data) == 2
    assert data[0] == pytest.approx([2, 4, 7])
    assert data[1] == pytest.approx([4, 4, 8])


@requires_fits  # only for AstroSession, but not worth being clever
@pytest.mark.parametrize("session,kwargs",
                         [(Session, {}), (AstroSession, {"ascii": True})])
@pytest.mark.parametrize("idval", [None, 1, "bob"])
def test_save_resid_ascii(session, kwargs, idval, tmp_path):
    """Can we use save_resid?"""

    s = session()
    outfile = tmp_path / "resid.dat"
    save_ascii_file(s, kwargs, idval, outfile, s.save_resid)

    names, data = get_data(outfile, ncols=2)
    assert names == ["X", "RESID"]
    assert len(data) == 2
    assert data[0] == pytest.approx([2, 4, 7])
    assert data[1] == pytest.approx([-1, 0, -3])


@requires_fits  # only for AstroSession, but not worth being clever
@pytest.mark.parametrize("session,kwargs",
                         [(Session, {}), (AstroSession, {"ascii": True})])
@pytest.mark.parametrize("idval", [None, 1, "bob"])
def test_save_delchi_ascii(session, kwargs, idval, tmp_path):
    """Can we use save_delchi?"""

    s = session()
    outfile = tmp_path / "resid.dat"
    save_ascii_file(s, kwargs, idval, outfile, s.save_delchi)

    names, data = get_data(outfile, ncols=2)
    assert names == ["X", "DELCHI"]
    assert len(data) == 2
    assert data[0] == pytest.approx([2, 4, 7])
    assert data[1] == pytest.approx([-1, 0, -0.5])


@requires_fits  # only for AstroSession, but not worth being clever
@pytest.mark.parametrize("session,kwargs",
                         [(Session, {}), (AstroSession, {"ascii": True})])
@pytest.mark.parametrize("idval", [None, 1, "bob"])
def test_save_data_ascii(session, kwargs, idval, tmp_path):
    """Can we use save_data?"""

    s = session()
    outfile = tmp_path / "data.dat"
    save_ascii_file(s, kwargs, idval, outfile, s.save_data)

    print(outfile.read_text())

    names, data = get_data(outfile, ncols=4)
    assert names == ["XLO", "XHI", "Y", "STATERROR"]
    assert len(data) == 4
    assert data[0] == pytest.approx([1, 3, 5])
    assert data[1] == pytest.approx([3, 5, 9])
    assert data[2] == pytest.approx([3, 4, 5])
    assert data[3] == pytest.approx([1, 2, 6])


@requires_fits  # only for AstroSession, but not worth being clever
@pytest.mark.parametrize("session,kwargs",
                         [(Session, {}), (AstroSession, {"ascii": True})])
@pytest.mark.parametrize("idval", [None, 1, "bob"])
def test_save_staterror_ascii(session, kwargs, idval, tmp_path):
    """Can we use save_staterror?

    The output of this looks wrong (just showing the XLO values not
    XMID or XLO,XHI) but treat as a regression test. See #1526.

    """

    s = session()
    outfile = tmp_path / "errs.dat"
    save_ascii_file(s, kwargs, idval, outfile, s.save_staterror)

    names, data = get_data(outfile, ncols=2)
    assert names == ["X", "STAT_ERR"]
    assert len(data) == 2
    assert data[0] == pytest.approx([1, 3, 5])
    assert data[1] == pytest.approx([1, 2, 6])


@requires_fits  # only for AstroSession, but not worth being clever
@pytest.mark.parametrize("session,kwargs",
                         [(Session, {}), (AstroSession, {"ascii": True})])
@pytest.mark.parametrize("idval", [None, 1, "bob"])
def test_save_syserror_ascii(session, kwargs, idval, tmp_path):
    """Can we use save_syserror?

    The output of this looks wrong (just showing the XLO values not
    XMID or XLO,XHI) but treat as a regression test. See #1526.

    """

    s = session()
    outfile = tmp_path / "errs.dat"
    save_ascii_file(s, kwargs, idval, outfile, s.save_syserror, syserr=True)

    names, data = get_data(outfile, ncols=2)
    assert names == ["X", "SYS_ERR"]
    assert len(data) == 2
    assert data[0] == pytest.approx([1, 3, 5])
    assert data[1] == pytest.approx([1, 2, 6])


@requires_fits  # only for AstroSession, but not worth being clever
@pytest.mark.parametrize("session,kwargs",
                         [(Session, {}), (AstroSession, {"ascii": True})])
@pytest.mark.parametrize("idval", [None, 1, "bob"])
def test_save_syserror_no_data_ascii(session, kwargs, idval, tmp_path):
    """Check save_syserror needs a systematic-error column."""

    s = session()
    outfile = tmp_path / "errs.dat"

    mid = 1 if idval is None else idval
    with pytest.raises(DataErr,
                       match=f"^data set '{mid}' does not specify systematic errors$"):
        save_ascii_file(s, kwargs, idval, outfile, s.save_syserror)


@requires_fits  # only for AstroSession, but not worth being clever
@pytest.mark.parametrize("session,kwargs",
                         [(Session, {}), (AstroSession, {"ascii": True})])
@pytest.mark.parametrize("idval", [None, 1, "bob"])
def test_save_error_ascii(session, kwargs, idval, tmp_path):
    """Can we use save_error?

    This does not bother testing the various combinations of
    statistical and systematic errors as this is assumed tested
    elsewhere.

    The output of this looks wrong (just showing the XLO values not
    XMID or XLO,XHI) but treat as a regression test.

    """

    s = session()
    outfile = tmp_path / "errs.dat"
    save_ascii_file(s, kwargs, idval, outfile, s.save_error)

    names, data = get_data(outfile, ncols=2)
    assert names == ["X", "ERR"]
    assert len(data) == 2
    assert data[0] == pytest.approx([1, 3, 5])
    assert data[1] == pytest.approx([1, 2, 6])


@pytest.mark.parametrize("session,flag",
                         [(Session, False),
                          (AstroSession, True)])
def test_show_data(session, flag):
    """Is show_data doing anything sensible?"""

    s = session()

    s.load_arrays(1, [-300, -100], [-150, -50], [-200, -100], Data1DInt)
    s.load_arrays(2, [1, 2, 10, 20], [3, 5, 12, 20])

    out = StringIO()
    s.show_data(outfile=out)

    toks = out.getvalue().split("\n")
    print(out.getvalue())
    assert toks[0] == "Data Set: 1"
    idx = 1
    if flag:
        assert toks[idx] == "Filter: -300.0000--50.0000 x"
        idx += 1

    assert toks[idx] == "name      = "
    idx += 1
    assert toks[idx] == "xlo       = Int64[2]"
    idx += 1
    assert toks[idx] == "xhi       = Int64[2]"
    idx += 1
    assert toks[idx] == "y         = Int64[2]"
    idx += 1
    assert toks[idx] == "staterror = None"
    idx += 1
    assert toks[idx] == "syserror  = None"
    idx += 1
    assert toks[idx] == ""
    idx += 1
    assert toks[idx] == "Data Set: 2"
    idx += 1

    if flag:
        assert toks[idx] == "Filter: 1.0000-20.0000 x"
        idx += 1

    assert toks[idx] == "name      = "
    idx += 1
    assert toks[idx] == "x         = Int64[4]"
    idx += 1
    assert toks[idx] == "y         = Int64[4]"
    idx += 1
    assert toks[idx] == "staterror = None"
    idx += 1
    assert toks[idx] == "syserror  = None"
    idx += 1
    assert toks[idx] == ""
    idx += 1
    assert toks[idx] == ""
    idx += 1
    assert toks[idx] == ""

    n = 19 if flag else 17
    assert len(toks) == n


@pytest.mark.parametrize("session", [Session, AstroSession])
def test_show_method(session):
    """Is show_method doing anything sensible?"""

    s = session()

    # Select the method so we are not affected if the default changes.
    #
    s.set_method("levmar")

    out = StringIO()
    s.show_method(outfile=out)

    toks = out.getvalue().split("\n")
    assert toks[0] == "Optimization Method: LevMar"
    assert toks[1] == "name     = levmar"
    assert toks[2] == "ftol     = 1.1920928955078125e-07"
    assert toks[3] == "xtol     = 1.1920928955078125e-07"
    assert toks[4] == "gtol     = 1.1920928955078125e-07"
    assert toks[5] == "maxfev   = None"
    assert toks[6] == "epsfcn   = 1.1920928955078125e-07"
    assert toks[7] == "factor   = 100.0"
    assert toks[8] == "numcores = 1"
    assert toks[9] == "verbose  = 0"
    assert toks[10] == ""
    assert toks[11] == ""

    assert len(toks) == 12


@pytest.mark.parametrize("session", [Session, AstroSession])
def test_show_stat(session):
    """Is show_stat doing anything sensible?"""

    s = session()

    # Select the statistic so we are not affected if the default changes.
    #
    s.set_stat("leastsq")

    out = StringIO()
    s.show_stat(outfile=out)

    # The statistic visualization is rather large and will change
    # whenever the docstring changes, so just check the start of the
    # output.
    #
    toks = out.getvalue().split("\n")
    assert toks[0] == "Statistic: LeastSq"
    assert toks[1] == "Least Squared Statistic."
    assert toks[2] == ""


@pytest.mark.parametrize("session", [Session, AstroSession])
def test_show_fit(session):
    """Cover a number of internal routines to check show_fit works."""

    s = session()
    s._add_model_types(sherpa.models.basic)

    # Have a model for datasets 1 and 2 but only fit to 2
    s.load_arrays(1, [-300, -100], [-200, -100])
    s.load_arrays(2, [1, 2, 10, 20], [3, 5, 12, 20])

    mdl1 = s.create_model_component("const1d", "mdl1")
    mdl2 = s.create_model_component("gauss1d", "mdl2")
    mdl3 = s.create_model_component("polynom1d", "mdl3")

    s.set_source(1, mdl1 + mdl2)
    s.set_source(2, mdl1 + mdl3)
    mdl3.c0 = 0
    mdl3.c0.freeze()
    mdl3.c1.thaw()

    s.set_stat("leastsq")
    s.set_method("simplex")

    s.fit(2)
    assert s.calc_stat(2) == pytest.approx(0.9473684210526329)
    assert mdl1.c0.val == pytest.approx(2.804511278195664)
    assert mdl3.c1.val == pytest.approx(0.8721804511277418)

    out = StringIO()
    s.show_fit(outfile=out)

    # The following is somethiing that will need to be changed
    # whenever an underlying object has it's string representation
    # changed, but it should not be hard to do. The main issue is
    # going to be numeric precision.
    #
    toks = out.getvalue().split("\n")
    assert toks[0] == "Optimization Method: NelderMead"
    assert toks[1] == "name         = simplex"
    assert toks[2] == "ftol         = 1.1920928955078125e-07"
    assert toks[3] == "maxfev       = None"
    assert toks[4] == "initsimplex  = 0"
    assert toks[5] == "finalsimplex = 9"
    assert toks[6] == "step         = None"
    assert toks[7] == "iquad        = 1"
    assert toks[8] == "verbose      = 0"
    assert toks[9] == "reflect      = True"
    assert toks[10] == ""
    assert toks[11] == "Statistic: LeastSq"
    assert toks[12] == "Least Squared Statistic."
    assert toks[13] == ""
    assert toks[14] == "    The least-square statistic is equivalent to a chi-square"
    assert toks[15] == "    statistic where the error on each point - sigma(i) - is 1."
    assert toks[16] == ""
    assert toks[17] == "    "
    assert toks[18] == ""
    assert toks[19] == "Fit:Dataset               = 2"
    assert toks[20] == "Method                = neldermead"
    assert toks[21] == "Statistic             = leastsq"
    assert toks[22] == "Initial fit statistic = 502"
    assert toks[23] == "Final fit statistic   = 0.947368 at function evaluation 233"
    assert toks[24] == "Data points           = 4"
    assert toks[25] == "Degrees of freedom    = 2"
    assert toks[26] == "Change in statistic   = 501.053"
    assert toks[27] == "   mdl1.c0        2.80451     "
    assert toks[28] == "   mdl3.c1        0.87218     "
    assert toks[29] == ""
    assert toks[30] == ""
    assert toks[31] == ""

    assert len(toks) == 32


@pytest.mark.parametrize("session", [Session, AstroSession])
@pytest.mark.parametrize("label", ["proj", "unc"])
def test_get_int_xxx_recalc_false(session, label):
    """Check we call the recalc=False path, even with no data loaded."""

    s = session()
    getfunc= getattr(s, f"get_int_{label}")
    plotobj = getfunc(recalc=False)

    name = "Uncertainty" if label == "unc" else "Projection"
    expected = getattr(sherpa.plot, f"Interval{name}")
    assert isinstance(plotobj, expected)

    # check it's empty (only need a single field check)
    assert plotobj.x is None


@pytest.mark.parametrize("session", [Session, AstroSession])
@pytest.mark.parametrize("label", ["proj", "unc"])
def test_get_reg_xxx_recalc_false(session, label):
    """Check we call the recalc=False path, even with no data loaded."""

    s = session()
    getfunc= getattr(s, f"get_reg_{label}")
    plotobj = getfunc(recalc=False)

    name = "Uncertainty" if label == "unc" else "Projection"
    expected = getattr(sherpa.plot, f"Region{name}")
    assert isinstance(plotobj, expected)

    # check it's empty (only need a single field check)
    assert plotobj.x0 is None


def setup_template_model(session, make_data_path, interp="default"):
    """Create the template model.

    The interp argument is passed to load_template_model as the
    template_interpolator_name field: we currently don't have a lot of
    documentation on what this is, but there is a code path which
    allows it to be set to None, which currently triggers different
    code paths, so it has been added to test this.

    The logic is test_309() from
    sherpa/models/tests/test_template_unit.py as this appears to be
    the only test of template models with the UI we have.

    """

    ynorm = 1e9  # make the values nicer

    # Need to load the data from the same directory as the index
    basedir = os.getcwd()
    os.chdir(make_data_path(""))
    try:
        session.load_template_model("bbtemp", "bb_index.dat",
                                    template_interpolator_name=interp)
    finally:
        os.chdir(basedir)

    bbtemp = session.get_model_component("bbtemp")
    return bbtemp, ynorm


@requires_data
@requires_fits  # only for AstroSession, but not worth being clever
@pytest.mark.parametrize("session", [Session, AstroSession])
@pytest.mark.parametrize("label", ["model", "source"])
def test_get_xxx_component_plot_with_templates_recalc_true(session, label, make_data_path):
    """What is the intended behavior for template models?

    This is a regression test as it is not obvious what the intended
    logic is. It was added to ensure a code path was tested, but
    this code path is highly-dependent on how the underlying code
    is written.

    """

    # This sets up a template model for the default id, so try
    # calling with this model but a different dataset.
    #
    s = session()
    dname = make_data_path('load_template_with_interpolation-bb_data.dat')
    s.load_data(dname)

    bbtemp, ynorm = setup_template_model(s, make_data_path)
    s.set_source(ynorm * bbtemp)

    with pytest.raises(IdentifierErr,
                       match="data set 2 has not been set"):
        getattr(s, f"get_{label}_component_plot")(2, bbtemp, recalc=True)


@requires_data
@requires_fits  # only for AstroSession, but not worth being clever
@pytest.mark.parametrize("session", [Session, AstroSession])
@pytest.mark.parametrize("label", ["model", "source"])
def test_get_xxx_component_plot_with_templates_recalc_true_no_interp(session, label, make_data_path):
    """What is the intended behavior for template models?

    Try to catch all code paths.

    """

    # This sets up a template model for the default id, so try
    # calling with this model but a different dataset.
    #
    s = session()
    dname = make_data_path('load_template_with_interpolation-bb_data.dat')
    s.load_data(dname)

    bbtemp, ynorm = setup_template_model(s, make_data_path, interp=None)
    s.set_source(ynorm * bbtemp)

    with pytest.raises(IdentifierErr,
                       match="data set 2 has not been set"):
        getattr(s, f"get_{label}_component_plot")(2, bbtemp, recalc=True)


@requires_data
@requires_fits  # only for AstroSession, but not worth being clever
@pytest.mark.parametrize("session", [Session, AstroSession])
@pytest.mark.parametrize("label", ["model", "source"])
def test_get_xxx_component_plot_with_templates_recalc_false(session, label, make_data_path):
    """What is the intended behavior for template models?

    This is a regression test as it is not obvious what the intended
    logic is. It was added to ensure a code path was tested, but
    this code path is highly-dependent on how the underlying code
    is written.

    """

    # This sets up a template model for the default id, so try
    # calling with this model but a different dataset.
    #
    s = session()
    dname = make_data_path('load_template_with_interpolation-bb_data.dat')
    s.load_data(dname)

    bbtemp, ynorm = setup_template_model(s, make_data_path)
    s.set_source(ynorm * bbtemp)

    # The plot results should be empty
    #
    mplot = getattr(s, f"get_{label}_plot")(2, recalc=False)
    cplot = getattr(s, f"get_{label}_component_plot")(2, bbtemp, recalc=False)

    mclass = getattr(sherpa.plot, f"{label.capitalize()}Plot")
    assert isinstance(mplot, mclass)

    cclass = getattr(sherpa.plot, f"Component{label.capitalize()}Plot")
    assert isinstance(cplot, cclass)

    # Check it's not a sub-class.
    #
    subclass = getattr(sherpa.plot, f"ComponentTemplate{label.capitalize()}Plot")
    assert not isinstance(cplot, subclass)

    assert mplot.x is None
    assert cplot.x is None
    assert mplot.title == label.capitalize()
    assert cplot.title == label.capitalize()


@requires_data
@requires_fits  # only for AstroSession, but not worth being clever
@pytest.mark.parametrize("session", [Session, AstroSession])
@pytest.mark.parametrize("label", ["model", "source"])
def test_get_xxx_component_plot_with_templates_recalc_false_no_interp(session, label, make_data_path):
    """What is the intended behavior for template models?

    This is a regresion test.

    """

    # This sets up a template model for the default id, so try
    # calling with this model but a different dataset.
    #
    s = session()
    dname = make_data_path('load_template_with_interpolation-bb_data.dat')
    s.load_data(dname)

    bbtemp, ynorm = setup_template_model(s, make_data_path, interp=None)
    s.set_source(ynorm * bbtemp)

    # The plot results should be empty
    #
    mplot = getattr(s, f"get_{label}_plot")(2, recalc=False)
    cplot = getattr(s, f"get_{label}_component_plot")(2, bbtemp, recalc=False)

    mclass = getattr(sherpa.plot, f"{label.capitalize()}Plot")
    assert isinstance(mplot, mclass)

    cclass = getattr(sherpa.plot, f"Component{label.capitalize()}Plot")
    assert isinstance(cplot, cclass)

    # The logic here is not-at-all obvious, but just test the current
    # behavior.
    #
    subclass = getattr(sherpa.plot, f"ComponentTemplate{label.capitalize()}Plot")
    if label == "source":
        assert isinstance(cplot, subclass)
    else:
        assert not isinstance(cplot, subclass)

    assert mplot.x is None
    assert cplot.x is None
    assert mplot.title == label.capitalize()
    assert cplot.title == label.capitalize()


@requires_data
@requires_fits  # only for AstroSession, but not worth being clever
@pytest.mark.parametrize("session", [Session, AstroSession])
@pytest.mark.parametrize("label", ["model", "source"])
def test_get_xxx_component_plot_with_templates_data1d(session, label, make_data_path):
    """What is the intended behavior for template models?  Data1D

    As this is not a PHA data set the source and model values should
    be the same (although plot labels will be different).

    This is a regression test as it is not obvious what the intended
    logic is.

    """

    s = session()
    dname = make_data_path('load_template_with_interpolation-bb_data.dat')
    s.load_data(dname)
    bbtemp, ynorm = setup_template_model(s, make_data_path)
    s.set_source(bbtemp * ynorm)

    # Because the source model is a composite, the y values of the
    # two should differ by ynorm.
    #
    mplot = getattr(s, f"get_{label}_plot")()
    cplot = getattr(s, f"get_{label}_component_plot")(bbtemp)

    mclass = getattr(sherpa.plot, f"{label.capitalize()}Plot")
    assert isinstance(mplot, mclass)

    cclass = getattr(sherpa.plot, f"Component{label.capitalize()}Plot")
    assert isinstance(cplot, cclass)

    # Check it's not a sub-class.
    #
    subclass = getattr(sherpa.plot, f"ComponentTemplate{label.capitalize()}Plot")
    assert not isinstance(cplot, subclass)

    # Make sure we have a valid set of y values, even if we do
    # not check the actual values.
    #
    assert mplot.y == pytest.approx(cplot.y * ynorm)
    assert numpy.all(mplot.y > 0)


@requires_data
@requires_fits  # only for AstroSession, but not worth being clever
@pytest.mark.parametrize("session", [Session, AstroSession])
@pytest.mark.parametrize("label", ["model", "source"])
def test_get_xxx_component_plot_with_templates_data1d_no_interp(session, label, make_data_path):
    """What is the intended behavior for template models?  Data1D, no interpolator

    As this is not a PHA data set the source and model values should
    be the same (although plot labels will be different).

    This is a regression test as it is not obvious what the intended
    logic is.

    """

    s = session()
    dname = make_data_path('load_template_with_interpolation-bb_data.dat')
    s.load_data(dname)
    bbtemp, ynorm = setup_template_model(s, make_data_path, interp=None)
    s.set_source(bbtemp * ynorm)

    # Because the source model is a composite, the y values of the
    # two should differ by ynorm.
    #
    mplot = getattr(s, f"get_{label}_plot")()
    cplot = getattr(s, f"get_{label}_component_plot")(bbtemp)

    mclass = getattr(sherpa.plot, f"{label.capitalize()}Plot")
    assert isinstance(mplot, mclass)

    cclass = getattr(sherpa.plot, f"Component{label.capitalize()}Plot")
    assert isinstance(cplot, cclass)

    # The logic here is not-at-all obvious, but just test the current
    # behavior.
    #
    subclass = getattr(sherpa.plot, f"ComponentTemplate{label.capitalize()}Plot")
    if label == "source":
        assert isinstance(cplot, subclass)
    else:
        assert not isinstance(cplot, subclass)

    # Make sure we have a valid set of y values, even if we do
    # not check the actual values.
    #
    assert mplot.y == pytest.approx(cplot.y * ynorm)
    assert numpy.all(mplot.y > 0)


@requires_data
@pytest.mark.parametrize("session", [Session, AstroSession])
@pytest.mark.parametrize("label", ["model", "source"])
def test_get_xxx_component_plot_with_templates_data1dint(session, label, make_data_path):
    """What is the intended behavior for template models?  Data1DInt"""

    s = session()

    # The actual data isn't too relevant, but pick similar x range
    # to load_template_with_interpolation-bb_data.dat
    #
    edges = numpy.arange(1, 3, 0.1) * 1e14
    s.load_arrays(1, edges[:-1], edges[1:], edges[1:] * 0, Data1DInt)

    bbtemp, ynorm = setup_template_model(s, make_data_path)
    s.set_source(bbtemp * ynorm)

    # Because the source model is a composite, the y values of the
    # two should differ by ynorm.
    #
    mplot = getattr(s, f"get_{label}_plot")()
    cplot = getattr(s, f"get_{label}_component_plot")(bbtemp)

    mclass = getattr(sherpa.plot, f"{label.capitalize()}HistogramPlot")
    assert isinstance(mplot, mclass)

    cclass = getattr(sherpa.plot, f"Component{label.capitalize()}HistogramPlot")
    assert isinstance(cplot, cclass)

    # Check it's not a sub-class.
    #
    subclass = getattr(sherpa.plot, f"ComponentTemplate{label.capitalize()}Plot")
    assert not isinstance(cplot, subclass)

    # Make sure we have a valid set of y values, even if we do
    # not check the actual values.
    #
    assert mplot.y == pytest.approx(cplot.y * ynorm)
    assert numpy.all(mplot.y > 0)


@requires_data
@pytest.mark.parametrize("session", [Session, AstroSession])
@pytest.mark.parametrize("label", ["model", "source"])
def test_get_xxx_component_plot_with_templates_data1dint_no_interp(session, label, make_data_path):
    """What is the intended behavior for template models?  Data1DInt, no interpolator"""

    s = session()

    # The actual data isn't too relevant, but pick similar x range
    # to load_template_with_interpolation-bb_data.dat
    #
    edges = numpy.arange(1, 3, 0.1) * 1e14
    s.load_arrays(1, edges[:-1], edges[1:], edges[1:] * 0, Data1DInt)

    bbtemp, ynorm = setup_template_model(s, make_data_path, interp=None)
    s.set_source(bbtemp * ynorm)

    # Because the source model is a composite, the y values of the
    # two should differ by ynorm.
    #
    mplot = getattr(s, f"get_{label}_plot")()
    cplot = getattr(s, f"get_{label}_component_plot")(bbtemp)

    mclass = getattr(sherpa.plot, f"{label.capitalize()}HistogramPlot")
    assert isinstance(mplot, mclass)

    # The logic here is not-at-all obvious, but just test the current
    # behavior.
    #
    # NOTE THE DIFFERENCE TO Data1DInt with interpolator whem label=spirce
    #
    if label == "source":
        assert isinstance(cplot, sherpa.plot.ComponentTemplateSourcePlot)

        # Unlike the normal Data1DInt case we can not compare the two
        # plots, so just add some regression tests for now.
        #
        assert len(mplot.y) == 19
        assert len(cplot.y) == 100

        assert mplot.y[0] == pytest.approx(cplot.y[0] * ynorm)
        assert numpy.all(mplot.y > 0)
        assert numpy.all(cplot.y > 0)

    else:

        assert isinstance(cplot, sherpa.plot.ComponentModelHistogramPlot)

        # Check it's not a sub-class.
        #
        assert not isinstance(cplot, sherpa.plot.ComponentTemplateModelPlot)

        # Make sure we have a valid set of y values, even if we do
        # not check the actual values.
        #
        assert mplot.y == pytest.approx(cplot.y * ynorm)
        assert numpy.all(mplot.y > 0)


@requires_data
@pytest.mark.parametrize("interp", ["default", None])
def test_get_source_component_plot_with_templates_datapha(interp, make_data_path):
    """What is the intended behavior for template models?  Data1PHA, with and without interpolator

    It would be nice to be able to check both source and model
    commands with a single test, but the behavior is not guaranteed to
    match.  This is a regression test as it's not clear what the
    behavior should be.

    """

    s = AstroSession()

    # The actual data isn't too relevant, but pick similar x range
    # to load_template_with_interpolation-bb_data.dat
    #
    chans = numpy.arange(1, 100, dtype=numpy.int16)
    s.load_arrays(1, chans, chans * 0, DataPHA)

    edges = numpy.linspace(1, 3, num=len(chans) + 1) * 1e4
    arf = create_arf(edges[:-1], edges[1:])
    s.set_arf(arf)

    bbtemp, ynorm = setup_template_model(s, make_data_path, interp=interp)
    s.set_source(bbtemp * ynorm)

    # Because the source model is a composite, the y values of the
    # two should differ by ynorm.
    #
    mplot = s.get_source_plot()
    cplot = s.get_source_component_plot(bbtemp)

    assert isinstance(mplot, sherpa.astro.plot.SourcePlot)
    assert isinstance(cplot, sherpa.astro.plot.ComponentSourcePlot)

    # Make sure we have a valid set of y values, even if we do
    # not check the actual values.
    #
    assert mplot.y == pytest.approx(cplot.y * ynorm)
    assert numpy.all(mplot.y > 0)


@requires_data
@pytest.mark.parametrize("interp", ["default", None])
def test_get_model_component_plot_with_templates_datapha(interp, make_data_path):
    """What is the intended behavior for template models?  Data1PHA, with and without interpolator

    It would be nice to be able to check both source and model
    commands with a single test, but the behavior is not guaranteed to
    match.  This is a regression test as it's not clear what the
    behavior should be.

    """

    s = AstroSession()

    # The actual data isn't too relevant, but pick similar x range
    # to load_template_with_interpolation-bb_data.dat
    #
    chans = numpy.arange(1, 100, dtype=numpy.int16)
    s.load_arrays(1, chans, chans * 0, DataPHA)

    edges = numpy.linspace(1, 3, num=len(chans) + 1) * 1e4
    arf = create_arf(edges[:-1], edges[1:])
    s.set_arf(arf)

    bbtemp, ynorm = setup_template_model(s, make_data_path, interp=interp)
    s.set_source(bbtemp * ynorm)

    # Because the source model is a composite, the y values of the
    # two should differ by ynorm.
    #
    mplot = s.get_model_plot()
    cplot = s.get_model_component_plot(bbtemp)

    assert isinstance(mplot, sherpa.astro.plot.ModelHistogram)
    assert isinstance(cplot, sherpa.astro.plot.ComponentModelPlot)

    # Make sure we have a valid set of y values, even if we do
    # not check the actual values.
    #
    assert mplot.y == pytest.approx(cplot.y * ynorm)
    assert numpy.all(mplot.y > 0)


@requires_data
@pytest.mark.parametrize("interp", ["default", None])
def test_compare_get_model_component_plot_with_templates(interp, make_data_path):
    """Check what happens comparing DataPHA with Data1DInt and Data1D

    This is a regression test as it is not clear what the intended
    behavior is.

    """

    NBINS = 100
    SPECRESP = 0.8
    BIN_WIDTH = 200

    s = AstroSession()

    # Create a dataset with the same "x" axis. This is not technically
    # possible, but knowing how model evaluation works (the first
    # array is normally used for 1D non-integrated) we can try
    # and get the same values used.
    #
    chans = numpy.arange(1, NBINS + 1, dtype=numpy.int16)
    s.load_arrays("pha", chans, chans * 0, DataPHA)

    # Give the ARF a non-unit response so we can see if it has been
    # applied (or, can infer it has been applied since the model
    # component will apply it).
    #
    edges = numpy.arange(10000, 30001, BIN_WIDTH)
    arf = create_arf(edges[:-1], edges[1:], numpy.ones(NBINS) * SPECRESP)
    s.set_arf("pha", arf)

    ones = numpy.ones(NBINS)
    s.load_arrays("int", edges[:-1], edges[1:], ones, Data1DInt)
    s.load_arrays("1d", edges[:-1], ones, Data1D)

    bbtemp, ynorm = setup_template_model(s, make_data_path, interp=interp)
    s.set_source("pha", bbtemp * ynorm)
    s.set_source("int", bbtemp * ynorm)
    s.set_source("1d", bbtemp * ynorm)

    mplot_pha = s.get_model_plot("pha")
    cplot_pha = s.get_model_component_plot("pha", bbtemp)

    mplot_int = s.get_model_plot("int")
    cplot_int = s.get_model_component_plot("int", bbtemp)

    mplot_1d = s.get_model_plot("1d")
    cplot_1d = s.get_model_component_plot("1d", bbtemp)

    # In case the pathway is different from using the default dataset
    # identifier, check some basic things about the response.
    #
    assert numpy.all(cplot_pha.y > 0)
    assert numpy.all(cplot_int.y > 0)
    assert numpy.all(cplot_1d.y > 0)

    assert cplot_int.xlo == pytest.approx(cplot_pha.xlo)
    assert cplot_1d.x == pytest.approx(cplot_pha.xlo)

    # It looks like the model is not integrated across the bin for
    # the 1DInt case.
    #
    assert cplot_1d.y == pytest.approx(cplot_int.y)

    # The DataPHA result, when compared to Data1D is:
    #
    # a) multiplied by SPECRESP
    # b) divided by BIN_WIDTH
    #
    r = cplot_int.y / cplot_pha.y
    assert r == pytest.approx(ones * BIN_WIDTH / SPECRESP)


@requires_data
def test_get_source_component_plot_with_templates_datapha_no_response(make_data_path):
    """What is the behavior with no response?

    It would be nice to be able to check both source and model
    commands with a single test, but the behavior is not guaranteed to
    match.  This is a regression test as it's not clear what the
    behavior should be.

    """

    s = AstroSession()

    chans = numpy.arange(1, 100, dtype=numpy.int16)
    s.load_arrays(1, chans, chans * 0, DataPHA)

    bbtemp, ynorm = setup_template_model(s, make_data_path)
    s.set_source(bbtemp * ynorm)

    with pytest.raises(DataErr,
                       match="Response does not specify energy bins"):
        s.get_source_plot()

    with pytest.raises(DataErr,
                       match="Response does not specify energy bins"):
        s.get_source_component_plot(bbtemp)


@requires_data
def test_get_model_component_plot_with_templates_datapha_no_response(make_data_path):
    """What is the behavior with no response?

    It would be nice to be able to check both source and model
    commands with a single test, but the behavior is not guaranteed to
    match.  This is a regression test as it's not clear what the
    behavior should be.

    """

    s = AstroSession()

    chans = numpy.arange(1, 100, dtype=numpy.int16)
    s.load_arrays(1, chans, chans * 0, DataPHA)

    bbtemp, ynorm = setup_template_model(s, make_data_path)
    s.set_source(bbtemp * ynorm)

    with pytest.raises(DataErr,
                       match="^No instrument response found for dataset $"):
        s.get_model_plot()

    cplot = s.get_model_component_plot(bbtemp)
    assert cplot.title == "Model component: template.bbtemp"
    assert numpy.all(cplot.y > 0)
