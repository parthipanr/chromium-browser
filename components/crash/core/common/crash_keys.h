// Copyright 2015 The Chromium Authors. All rights reserved.
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.

#ifndef COMPONENTS_CRASH_CORE_COMMON_CRASH_KEYS_H_
#define COMPONENTS_CRASH_CORE_COMMON_CRASH_KEYS_H_

#include <string>

namespace base {
class CommandLine;
}  // namespace base

namespace crash_keys {

// Sets the ID (which may either be a full GUID or a GUID that was already
// stripped from its dashes -- in either case this method will strip remaining
// dashes before setting the crash key).
void SetMetricsClientIdFromGUID(const std::string& metrics_client_guid);
void ClearMetricsClientId();

// A function returning true if |flag| is a switch that should be filtered out
// of crash keys.
using SwitchFilterFunction = bool (*)(const std::string& flag);

// Sets the "num-switches" key and a set of keys named using kSwitchFormat based
// on the given |command_line|. If |skip_filter| is not null, ignore any switch
// for which it returns true.
void SetSwitchesFromCommandLine(const base::CommandLine& command_line,
                                SwitchFilterFunction skip_filter);

// Clears all the CommandLine-related crash keys.
void ResetCommandLineForTesting();

}  // namespace crash_keys

#endif  // COMPONENTS_CRASH_CORE_COMMON_CRASH_KEYS_H_
