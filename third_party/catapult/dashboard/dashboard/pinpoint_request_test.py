# Copyright 2017 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import json
import mock

import webapp2
import webtest

from dashboard import pinpoint_request
from dashboard.common import namespaced_stored_object
from dashboard.common import testing_common
from dashboard.common import utils
from dashboard.models import graph_data
from dashboard.services import pinpoint_service


class PinpointNewPrefillRequestHandlerTest(testing_common.TestCase):

  def setUp(self):
    super(PinpointNewPrefillRequestHandlerTest, self).setUp()

    app = webapp2.WSGIApplication(
        [(r'/pinpoint/new/prefill',
          pinpoint_request.PinpointNewPrefillRequestHandler)])
    self.testapp = webtest.TestApp(app)

  @mock.patch.object(
      pinpoint_request.start_try_job, 'GuessStoryFilter')
  def testPost_CallsGuessStoryFilter(self, mock_story_filter):
    mock_story_filter.return_value = 'bar'
    response = self.testapp.post('/pinpoint/new/prefill', {'test_path': 'foo'})
    self.assertEqual(
        {'story_filter': 'bar'}, json.loads(response.body))
    mock_story_filter.assert_called_with('foo')


class PinpointNewPerfTryRequestHandlerTest(testing_common.TestCase):

  def setUp(self):
    super(PinpointNewPerfTryRequestHandlerTest, self).setUp()

    app = webapp2.WSGIApplication(
        [(r'/pinpoint/new',
          pinpoint_request.PinpointNewPerfTryRequestHandler)])
    self.testapp = webtest.TestApp(app)

    self.SetCurrentUser('foo@chromium.org')

    namespaced_stored_object.Set('bot_configurations', {
        'mac': {
            'dimensions': [{'key': 'foo', 'value': 'mac_dimensions'}]
        },
        'android-webview-nexus5x': {
            'dimensions': [{'key': 'foo', 'value': 'android_dimensions'}]
        }
    })

    namespaced_stored_object.Set('repositories', {
        'chromium': {'some': 'params'},
        'v8': {'more': 'params'}
    })

    namespaced_stored_object.Set('bot_browser_map', [
        ['android-webview', 'webview'],
        ['', 'release']
    ])

  @mock.patch.object(
      utils, 'IsValidSheriffUser', mock.MagicMock(return_value=False))
  def testPost_NotSheriff(self):
    response = self.testapp.post('/pinpoint/new')
    self.assertEqual(
        {u'error': u'User "foo@chromium.org" not authorized.'},
        json.loads(response.body))

  @mock.patch.object(
      utils, 'IsValidSheriffUser', mock.MagicMock(return_value=True))
  @mock.patch.object(pinpoint_service, 'NewJob')
  @mock.patch.object(
      pinpoint_request, 'PinpointParamsFromPerfTryParams',
      mock.MagicMock(return_value={'test': 'result'}))
  def testPost_Succeeds(self, mock_pinpoint):
    mock_pinpoint.return_value = {'foo': 'bar'}
    self.SetCurrentUser('foo@chromium.org')
    params = {'a': 'b', 'c': 'd'}
    response = self.testapp.post('/pinpoint/new', params)

    expected_args = mock.call({'test': 'result'})
    self.assertEqual([expected_args], mock_pinpoint.call_args_list)
    self.assertEqual({'foo': 'bar'}, json.loads(response.body))

  @mock.patch.object(
      utils, 'IsValidSheriffUser', mock.MagicMock(return_value=False))
  def testPinpointParams_InvalidSheriff_RaisesError(self):
    params = {
        'test_path': 'ChromiumPerf/foo/blah/foo'
    }
    with self.assertRaises(pinpoint_request.InvalidParamsError):
      pinpoint_request.PinpointParamsFromPerfTryParams(params)

  @mock.patch.object(
      utils, 'IsValidSheriffUser', mock.MagicMock(return_value=True))
  def testPinpointParams_BotUndefined_ReturnsError(self):
    params = {
        'test_path': 'ChromiumPerf/foo/blah/foo',
        'bisect_mode': 'performance',
        'story_filter': '',
    }
    with self.assertRaises(pinpoint_request.InvalidParamsError):
      pinpoint_request.PinpointParamsFromPerfTryParams(params)

  @mock.patch.object(
      utils, 'IsValidSheriffUser', mock.MagicMock(return_value=True))
  def testPinpointParams_NonTelemetry_RaisesError(self):
    params = {
        'test_path': 'ChromiumPerf/mac/cc_perftests/foo',
        'start_commit': 'abcd1234',
        'end_commit': 'efgh5678',
        'start_repository': 'chromium',
        'end_repository': 'chromium',
    }
    with self.assertRaises(pinpoint_request.InvalidParamsError):
      pinpoint_request.PinpointParamsFromPerfTryParams(params)

  @mock.patch.object(
      utils, 'IsValidSheriffUser', mock.MagicMock(return_value=True))
  def testPinpointParams_IsolateTarget_Telemetry(self):
    params = {
        'test_path': 'ChromiumPerf/mac/system_health/foo',
        'start_commit': 'abcd1234',
        'end_commit': 'efgh5678',
        'start_repository': 'chromium',
        'end_repository': 'chromium',
        'extra_test_args': json.dumps(
            ['--extra-trace-args', 'abc,123,foo']),
    }
    results = pinpoint_request.PinpointParamsFromPerfTryParams(params)

    self.assertEqual('mac', results['configuration'])
    self.assertEqual('release', results['browser'])
    self.assertEqual('system_health', results['benchmark'])
    self.assertEqual('', results['chart'])
    self.assertEqual('telemetry_perf_tests', results['target'])
    self.assertEqual('foo@chromium.org', results['email'])
    self.assertEqual('chromium', results['start_repository'])
    self.assertEqual('abcd1234', results['start_git_hash'])
    self.assertEqual('chromium', results['end_repository'])
    self.assertEqual('efgh5678', results['end_git_hash'])
    self.assertEqual('0', results['auto_explore'])
    self.assertEqual('', results['bug_id'])
    self.assertEqual('', results['story'])
    self.assertEqual(
        ['--extra-trace-args', 'abc,123,foo'],
        json.loads(results['extra_test_args']))
    self.assertEqual(
        [{'key': 'foo', 'value': 'mac_dimensions'}],
        json.loads(results['dimensions']))

  @mock.patch.object(
      utils, 'IsValidSheriffUser', mock.MagicMock(return_value=True))
  def testPinpointParams_IsolateTarget_WebviewTelemetry(self):
    params = {
        'test_path': 'ChromiumPerf/android-webview-nexus5x/system_health/foo',
        'start_commit': 'abcd1234',
        'end_commit': 'efgh5678',
        'start_repository': 'chromium',
        'end_repository': 'chromium',
        'extra_test_args': '',
    }
    results = pinpoint_request.PinpointParamsFromPerfTryParams(params)

    self.assertEqual('android-webview-nexus5x', results['configuration'])
    self.assertEqual('webview', results['browser'])
    self.assertEqual('system_health', results['benchmark'])
    self.assertEqual('', results['chart'])
    self.assertEqual('telemetry_perf_webview_tests', results['target'])
    self.assertEqual('foo@chromium.org', results['email'])
    self.assertEqual('chromium', results['start_repository'])
    self.assertEqual('abcd1234', results['start_git_hash'])
    self.assertEqual('chromium', results['end_repository'])
    self.assertEqual('efgh5678', results['end_git_hash'])
    self.assertEqual('0', results['auto_explore'])
    self.assertEqual('', results['bug_id'])
    self.assertEqual(
        [{'key': 'foo', 'value': 'android_dimensions'}],
        json.loads(results['dimensions']))

  @mock.patch.object(
      utils, 'IsValidSheriffUser', mock.MagicMock(return_value=True))
  def testPinpointParams_StartRepositoryInvalid_RaisesError(self):
    params = {
        'test_path': 'ChromiumPerf/android-webview-nexus5x/system_health/foo',
        'start_commit': 'abcd1234',
        'end_commit': 'efgh5678',
        'start_repository': 'foo',
        'end_repository': 'chromium',
        'extra_test_args': '',
    }
    with self.assertRaises(pinpoint_request.InvalidParamsError):
      pinpoint_request.PinpointParamsFromPerfTryParams(params)

  @mock.patch.object(
      utils, 'IsValidSheriffUser', mock.MagicMock(return_value=True))
  def testPinpointParams_StartRepositoryNoChromium_RaisesError(self):
    params = {
        'test_path': 'ChromiumPerf/android-webview-nexus5x/system_health/foo',
        'start_commit': 'abcd1234',
        'end_commit': 'efgh5678',
        'start_repository': 'v8',
        'end_repository': 'chromium',
        'extra_test_args': '',
    }
    with self.assertRaises(pinpoint_request.InvalidParamsError):
      pinpoint_request.PinpointParamsFromPerfTryParams(params)

  @mock.patch.object(
      utils, 'IsValidSheriffUser', mock.MagicMock(return_value=True))
  def testPinpointParams_EndRepositoryNoChromium_RaisesError(self):
    params = {
        'test_path': 'ChromiumPerf/android-webview-nexus5x/system_health/foo',
        'start_commit': 'abcd1234',
        'end_commit': 'efgh5678',
        'start_repository': 'chromium',
        'end_repository': 'v8',
        'extra_test_args': '',
    }
    with self.assertRaises(pinpoint_request.InvalidParamsError):
      pinpoint_request.PinpointParamsFromPerfTryParams(params)

  @mock.patch.object(
      utils, 'IsValidSheriffUser', mock.MagicMock(return_value=True))
  @mock.patch.object(
      pinpoint_request.crrev_service, 'GetNumbering',
      mock.MagicMock(return_value={'git_sha': 'abcd'}))
  def testPinpointParams_ConvertsCommitsToGitHashes(self):
    params = {
        'test_path': 'ChromiumPerf/android-webview-nexus5x/system_health/foo',
        'start_commit': '1234',
        'end_commit': '5678',
        'start_repository': 'chromium',
        'end_repository': 'chromium',
        'extra_test_args': '',
    }
    results = pinpoint_request.PinpointParamsFromPerfTryParams(params)

    self.assertEqual('abcd', results['start_git_hash'])
    self.assertEqual('abcd', results['end_git_hash'])

  @mock.patch.object(
      utils, 'IsValidSheriffUser', mock.MagicMock(return_value=True))
  @mock.patch.object(
      pinpoint_request.crrev_service, 'GetNumbering')
  def testPinpointParams_SkipsConvertingHashes(self, mock_crrev):
    params = {
        'test_path': 'ChromiumPerf/android-webview-nexus5x/system_health/foo',
        'start_commit': 'abcd1234',
        'end_commit': 'efgh5678',
        'start_repository': 'chromium',
        'end_repository': 'chromium',
        'extra_test_args': '',
    }
    results = pinpoint_request.PinpointParamsFromPerfTryParams(params)

    self.assertEqual('abcd1234', results['start_git_hash'])
    self.assertEqual('efgh5678', results['end_git_hash'])
    self.assertFalse(mock_crrev.called)

  @mock.patch.object(
      utils, 'IsValidSheriffUser', mock.MagicMock(return_value=True))
  def testPinpointParams_InvalidRepositoryCommitPosition(self):
    params = {
        'test_path': 'ChromiumPerf/android-webview-nexus5x/system_health/foo',
        'start_commit': '123',
        'end_commit': '456',
        'start_repository': 'v8',
        'end_repository': 'v8',
        'extra_test_args': '',
    }
    with self.assertRaises(pinpoint_request.InvalidParamsError):
      pinpoint_request.PinpointParamsFromPerfTryParams(params)

  @mock.patch.object(
      utils, 'IsValidSheriffUser', mock.MagicMock(return_value=True))
  @mock.patch.object(
      pinpoint_request.crrev_service, 'GetNumbering',
      mock.MagicMock(return_value={'error': {'message': 'foo'}}))
  def testPinpointParams_CrrevFails(self):
    params = {
        'test_path': 'ChromiumPerf/android-webview-nexus5x/system_health/foo',
        'start_commit': '123',
        'end_commit': '456',
        'start_repository': 'v8',
        'end_repository': 'v8',
        'extra_test_args': '',
    }
    with self.assertRaises(pinpoint_request.InvalidParamsError):
      pinpoint_request.PinpointParamsFromPerfTryParams(params)



class PinpointNewBisectRequestHandlerTest(testing_common.TestCase):

  def setUp(self):
    super(PinpointNewBisectRequestHandlerTest, self).setUp()

    app = webapp2.WSGIApplication(
        [(r'/pinpoint/new',
          pinpoint_request.PinpointNewBisectRequestHandler)])
    self.testapp = webtest.TestApp(app)

    self.SetCurrentUser('foo@chromium.org')

    namespaced_stored_object.Set('bot_configurations', {
        'mac': {
            'dimensions': [{'key': 'foo', 'value': 'mac_dimensions'}]
        },
        'android-webview-nexus5x': {
            'dimensions': [{'key': 'foo', 'value': 'android_dimensions'}]
        }
    })

    namespaced_stored_object.Set('repositories', {
        'chromium': {'some': 'params'},
        'v8': {'more': 'params'}
    })

    namespaced_stored_object.Set('bot_browser_map', [
        ['android-webview', 'webview'],
        ['', 'release']
    ])

  @mock.patch.object(
      utils, 'IsValidSheriffUser', mock.MagicMock(return_value=False))
  def testPost_NotSheriff(self):
    response = self.testapp.post('/pinpoint/new')
    self.assertEqual(
        {u'error': u'User "foo@chromium.org" not authorized.'},
        json.loads(response.body))

  @mock.patch.object(
      utils, 'IsValidSheriffUser', mock.MagicMock(return_value=True))
  @mock.patch.object(pinpoint_service, 'NewJob')
  @mock.patch.object(
      pinpoint_request, 'PinpointParamsFromBisectParams',
      mock.MagicMock(return_value={'test': 'result'}))
  def testPost_Succeeds(self, mock_pinpoint):
    mock_pinpoint.return_value = {'foo': 'bar'}
    self.SetCurrentUser('foo@chromium.org')
    params = {'a': 'b', 'c': 'd'}
    response = self.testapp.post('/pinpoint/new', params)

    expected_args = mock.call({'test': 'result'})
    self.assertEqual([expected_args], mock_pinpoint.call_args_list)
    self.assertEqual({'foo': 'bar'}, json.loads(response.body))

  @mock.patch.object(
      utils, 'IsValidSheriffUser', mock.MagicMock(return_value=False))
  def testPinpointParams_InvalidSheriff_RaisesError(self):
    params = {
        'test_path': 'ChromiumPerf/foo/blah/foo'
    }
    with self.assertRaises(pinpoint_request.InvalidParamsError):
      pinpoint_request.PinpointParamsFromBisectParams(params)

  @mock.patch.object(
      utils, 'IsValidSheriffUser', mock.MagicMock(return_value=True))
  def testPinpointParams_BotUndefined_ReturnsError(self):
    params = {
        'test_path': 'ChromiumPerf/foo/blah/foo',
        'bisect_mode': 'performance',
        'story_filter': '',
    }
    with self.assertRaises(pinpoint_request.InvalidParamsError):
      pinpoint_request.PinpointParamsFromBisectParams(params)

  @mock.patch.object(
      utils, 'IsValidSheriffUser', mock.MagicMock(return_value=True))
  def testPinpointParams_IsolateTarget_NonTelemetry(self):
    params = {
        'test_path': 'ChromiumPerf/mac/cc_perftests/foo',
        'start_commit': 'abcd1234',
        'end_commit': 'efgh5678',
        'start_repository': 'chromium',
        'end_repository': 'chromium',
        'bug_id': 1,
        'bisect_mode': 'performance',
        'story_filter': '',
    }
    results = pinpoint_request.PinpointParamsFromBisectParams(params)

    self.assertEqual('mac', results['configuration'])
    self.assertEqual('release', results['browser'])
    self.assertEqual('cc_perftests', results['benchmark'])
    self.assertEqual('foo', results['chart'])
    self.assertEqual('cc_perftests', results['target'])
    self.assertEqual('foo@chromium.org', results['email'])
    self.assertEqual('chromium', results['start_repository'])
    self.assertEqual('abcd1234', results['start_git_hash'])
    self.assertEqual('chromium', results['end_repository'])
    self.assertEqual('efgh5678', results['end_git_hash'])
    self.assertEqual('1', results['auto_explore'])
    self.assertEqual(1, results['bug_id'])
    self.assertEqual(
        [{'key': 'foo', 'value': 'mac_dimensions'}],
        json.loads(results['dimensions']))

  @mock.patch.object(
      utils, 'IsValidSheriffUser', mock.MagicMock(return_value=True))
  def testPinpointParams_IsolateTarget_Telemetry(self):
    params = {
        'test_path': 'ChromiumPerf/mac/system_health/foo',
        'start_commit': 'abcd1234',
        'end_commit': 'efgh5678',
        'start_repository': 'chromium',
        'end_repository': 'chromium',
        'bug_id': 1,
        'story_filter': 'foo',
        'bisect_mode': 'performance',
    }
    results = pinpoint_request.PinpointParamsFromBisectParams(params)

    self.assertEqual('mac', results['configuration'])
    self.assertEqual('release', results['browser'])
    self.assertEqual('system_health', results['benchmark'])
    self.assertEqual('foo', results['chart'])
    self.assertEqual('telemetry_perf_tests', results['target'])
    self.assertEqual('foo@chromium.org', results['email'])
    self.assertEqual('chromium', results['start_repository'])
    self.assertEqual('abcd1234', results['start_git_hash'])
    self.assertEqual('chromium', results['end_repository'])
    self.assertEqual('efgh5678', results['end_git_hash'])
    self.assertEqual('1', results['auto_explore'])
    self.assertEqual(1, results['bug_id'])
    self.assertEqual('foo', results['story'])
    self.assertEqual(
        [{'key': 'foo', 'value': 'mac_dimensions'}],
        json.loads(results['dimensions']))

  @mock.patch.object(
      utils, 'IsValidSheriffUser', mock.MagicMock(return_value=True))
  def testPinpointParams_IsolateTarget_WebviewTelemetry(self):
    params = {
        'test_path': 'ChromiumPerf/android-webview-nexus5x/system_health/foo',
        'start_commit': 'abcd1234',
        'end_commit': 'efgh5678',
        'start_repository': 'chromium',
        'end_repository': 'chromium',
        'bug_id': 1,
        'bisect_mode': 'performance',
        'story_filter': '',
    }
    results = pinpoint_request.PinpointParamsFromBisectParams(params)

    self.assertEqual('android-webview-nexus5x', results['configuration'])
    self.assertEqual('webview', results['browser'])
    self.assertEqual('system_health', results['benchmark'])
    self.assertEqual('foo', results['chart'])
    self.assertEqual('telemetry_perf_webview_tests', results['target'])
    self.assertEqual('foo@chromium.org', results['email'])
    self.assertEqual('chromium', results['start_repository'])
    self.assertEqual('abcd1234', results['start_git_hash'])
    self.assertEqual('chromium', results['end_repository'])
    self.assertEqual('efgh5678', results['end_git_hash'])
    self.assertEqual('1', results['auto_explore'])
    self.assertEqual(1, results['bug_id'])
    self.assertEqual(
        [{'key': 'foo', 'value': 'android_dimensions'}],
        json.loads(results['dimensions']))

  @mock.patch.object(
      utils, 'IsValidSheriffUser', mock.MagicMock(return_value=True))
  def testPinpointParams_Metric_TopLevelOnly(self):
    params = {
        'test_path': 'ChromiumPerf/mac/blink_perf/foo',
        'start_commit': 'abcd1234',
        'end_commit': 'efgh5678',
        'start_repository': 'chromium',
        'end_repository': 'chromium',
        'bug_id': 1,
        'bisect_mode': 'performance',
        'story_filter': '',
    }
    results = pinpoint_request.PinpointParamsFromBisectParams(params)

    self.assertEqual('', results['tir_label'])
    self.assertEqual('foo', results['chart'])
    self.assertEqual('', results['trace'])

  @mock.patch.object(
      utils, 'IsValidSheriffUser', mock.MagicMock(return_value=True))
  def testPinpointParams_Metric_ChartAndTrace(self):
    params = {
        'test_path': 'ChromiumPerf/mac/blink_perf/foo/http___bar.html',
        'start_commit': 'abcd1234',
        'end_commit': 'efgh5678',
        'start_repository': 'chromium',
        'end_repository': 'chromium',
        'bug_id': 1,
        'bisect_mode': 'performance',
        'story_filter': '',
    }
    graph_data.TestMetadata(
        id=params['test_path'], unescaped_story_name='http://bar.html').put()
    results = pinpoint_request.PinpointParamsFromBisectParams(params)

    self.assertEqual('', results['tir_label'])
    self.assertEqual('foo', results['chart'])
    self.assertEqual('http://bar.html', results['trace'])

  @mock.patch.object(
      utils, 'IsValidSheriffUser', mock.MagicMock(return_value=True))
  def testPinpointParams_Metric_TIRLabelChartAndTrace(self):
    params = {
        'test_path': 'ChromiumPerf/mac/blink_perf/foo/label/bar.html',
        'start_commit': 'abcd1234',
        'end_commit': 'efgh5678',
        'start_repository': 'chromium',
        'end_repository': 'chromium',
        'bug_id': 1,
        'bisect_mode': 'performance',
        'story_filter': '',
    }
    graph_data.TestMetadata(id=params['test_path'],).put()
    results = pinpoint_request.PinpointParamsFromBisectParams(params)

    self.assertEqual('label', results['tir_label'])
    self.assertEqual('foo', results['chart'])
    self.assertEqual('bar.html', results['trace'])

  @mock.patch.object(
      utils, 'IsValidSheriffUser', mock.MagicMock(return_value=True))
  def testPinpointParams_BisectMode_Invalid_RaisesError(self):
    params = {
        'test_path': 'ChromiumPerf/mac/blink_perf/foo/label/bar.html',
        'start_commit': 'abcd1234',
        'end_commit': 'efgh5678',
        'start_repository': 'chromium',
        'end_repository': 'chromium',
        'bug_id': 1,
        'bisect_mode': 'foo',
        'story_filter': '',
    }
    graph_data.TestMetadata(id=params['test_path'],).put()
    with self.assertRaises(pinpoint_request.InvalidParamsError):
      pinpoint_request.PinpointParamsFromBisectParams(params)

  @mock.patch.object(
      utils, 'IsValidSheriffUser', mock.MagicMock(return_value=True))
  def testPinpointParams_BisectMode_Functional(self):
    params = {
        'test_path': 'ChromiumPerf/mac/blink_perf/foo/label/bar.html',
        'start_commit': 'abcd1234',
        'end_commit': 'efgh5678',
        'start_repository': 'chromium',
        'end_repository': 'chromium',
        'bug_id': 1,
        'bisect_mode': 'functional',
        'story_filter': '',
    }
    graph_data.TestMetadata(id=params['test_path'],).put()
    results = pinpoint_request.PinpointParamsFromBisectParams(params)

    self.assertEqual('', results['tir_label'])
    self.assertEqual('', results['chart'])
    self.assertEqual('', results['trace'])

  @mock.patch.object(
      utils, 'IsValidSheriffUser', mock.MagicMock(return_value=True))
  def testPinpointParams_StartRepositoryInvalid_RaisesError(self):
    params = {
        'test_path': 'ChromiumPerf/android-webview-nexus5x/system_health/foo',
        'start_commit': 'abcd1234',
        'end_commit': 'efgh5678',
        'start_repository': 'foo',
        'end_repository': 'chromium',
        'bisect_mode': 'performance',
        'story_filter': '',
    }
    with self.assertRaises(pinpoint_request.InvalidParamsError):
      pinpoint_request.PinpointParamsFromBisectParams(params)

  @mock.patch.object(
      utils, 'IsValidSheriffUser', mock.MagicMock(return_value=True))
  def testPinpointParams_StartRepositoryNoChromium_RaisesError(self):
    params = {
        'test_path': 'ChromiumPerf/android-webview-nexus5x/system_health/foo',
        'start_commit': 'abcd1234',
        'end_commit': 'efgh5678',
        'start_repository': 'v8',
        'end_repository': 'chromium',
        'bisect_mode': 'performance',
        'story_filter': '',
    }
    with self.assertRaises(pinpoint_request.InvalidParamsError):
      pinpoint_request.PinpointParamsFromBisectParams(params)

  @mock.patch.object(
      utils, 'IsValidSheriffUser', mock.MagicMock(return_value=True))
  def testPinpointParams_EndRepositoryNoChromium_RaisesError(self):
    params = {
        'test_path': 'ChromiumPerf/android-webview-nexus5x/system_health/foo',
        'start_commit': 'abcd1234',
        'end_commit': 'efgh5678',
        'start_repository': 'chromium',
        'end_repository': 'v8',
        'bisect_mode': 'performance',
        'story_filter': '',
    }
    with self.assertRaises(pinpoint_request.InvalidParamsError):
      pinpoint_request.PinpointParamsFromBisectParams(params)

  @mock.patch.object(
      utils, 'IsValidSheriffUser', mock.MagicMock(return_value=True))
  @mock.patch.object(
      pinpoint_request.crrev_service, 'GetNumbering',
      mock.MagicMock(return_value={'git_sha': 'abcd'}))
  def testPinpointParams_ConvertsCommitsToGitHashes(self):
    params = {
        'test_path': 'ChromiumPerf/android-webview-nexus5x/system_health/foo',
        'start_commit': '1234',
        'end_commit': '5678',
        'start_repository': 'chromium',
        'end_repository': 'chromium',
        'bug_id': '',
        'bisect_mode': 'performance',
        'story_filter': '',
    }
    results = pinpoint_request.PinpointParamsFromBisectParams(params)

    self.assertEqual('abcd', results['start_git_hash'])
    self.assertEqual('abcd', results['end_git_hash'])

  @mock.patch.object(
      utils, 'IsValidSheriffUser', mock.MagicMock(return_value=True))
  @mock.patch.object(
      pinpoint_request.crrev_service, 'GetNumbering')
  def testPinpointParams_SkipsConvertingHashes(self, mock_crrev):
    params = {
        'test_path': 'ChromiumPerf/android-webview-nexus5x/system_health/foo',
        'start_commit': 'abcd1234',
        'end_commit': 'efgh5678',
        'start_repository': 'chromium',
        'end_repository': 'chromium',
        'bug_id': '',
        'bisect_mode': 'performance',
        'story_filter': '',
    }
    results = pinpoint_request.PinpointParamsFromBisectParams(params)

    self.assertEqual('abcd1234', results['start_git_hash'])
    self.assertEqual('efgh5678', results['end_git_hash'])
    self.assertFalse(mock_crrev.called)

  @mock.patch.object(
      utils, 'IsValidSheriffUser', mock.MagicMock(return_value=True))
  def testPinpointParams_InvalidRepositoryCommitPosition(self):
    params = {
        'test_path': 'ChromiumPerf/android-webview-nexus5x/system_health/foo',
        'start_commit': '123',
        'end_commit': '456',
        'start_repository': 'v8',
        'end_repository': 'v8',
        'bisect_mode': 'performance',
        'story_filter': '',
    }
    with self.assertRaises(pinpoint_request.InvalidParamsError):
      pinpoint_request.PinpointParamsFromBisectParams(params)

  @mock.patch.object(
      utils, 'IsValidSheriffUser', mock.MagicMock(return_value=True))
  @mock.patch.object(
      pinpoint_request.crrev_service, 'GetNumbering',
      mock.MagicMock(return_value={'error': {'message': 'foo'}}))
  def testPinpointParams_CrrevFails(self):
    params = {
        'test_path': 'ChromiumPerf/android-webview-nexus5x/system_health/foo',
        'start_commit': '123',
        'end_commit': '456',
        'start_repository': 'v8',
        'end_repository': 'v8',
        'bisect_mode': 'performance',
        'story_filter': '',
    }
    with self.assertRaises(pinpoint_request.InvalidParamsError):
      pinpoint_request.PinpointParamsFromBisectParams(params)

  @mock.patch.object(
      utils, 'IsValidSheriffUser', mock.MagicMock(return_value=True))
  def testPinpointParams_SplitsStatistics(self):
    statistic_types = ['avg', 'min', 'max', 'sum', 'std', 'count']

    for s in statistic_types:
      params = {
          'test_path': 'ChromiumPerf/mac/system_health/foo_%s' % s,
          'start_commit': 'abcd1234',
          'end_commit': 'efgh5678',
          'start_repository': 'chromium',
          'end_repository': 'chromium',
          'bisect_mode': 'performance',
          'story_filter': '',
          'bug_id': -1,
      }
      results = pinpoint_request.PinpointParamsFromBisectParams(params)

      self.assertEqual(s, results['statistic'])
      self.assertEqual('foo', results['chart'])
