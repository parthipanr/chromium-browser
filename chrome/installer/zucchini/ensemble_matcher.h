// Copyright 2017 The Chromium Authors. All rights reserved.
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.

#ifndef CHROME_INSTALLER_ZUCCHINI_ENSEMBLE_MATCHER_H_
#define CHROME_INSTALLER_ZUCCHINI_ENSEMBLE_MATCHER_H_

#include <stddef.h>

#include <vector>

#include "base/macros.h"
#include "chrome/installer/zucchini/buffer_view.h"
#include "chrome/installer/zucchini/element_detection.h"
#include "chrome/installer/zucchini/image_utils.h"

namespace zucchini {

// A base class for ensemble matching strategies, which identify Elements in a
// "new" and "old" archives, and match each "new" Element to an "old" Element.
// Matched pairs can then be passed to Disassembler for architecture-specific
// patching. Notes:
// - A matched Element pair must have the same ExecutableType.
// - Special case: Exact matches are ignored, since they can be patched directly
//   without architecture-specific patching.
// - Multiple "new" Elements may match a common "old" Element.
// - A "new" Element may have no match. This can happen when no viable match
//   exists, or when an exact match is skipped.
class EnsembleMatcher {
 public:
  EnsembleMatcher();
  virtual ~EnsembleMatcher();

  // Interface to main matching feature. Returns whether match was successful.
  // This should be called at most once per instace.
  virtual bool RunMatch(ConstBufferView old_image,
                        ConstBufferView new_image) = 0;

  // Accessors to RunMatch() results.
  const std::vector<ElementMatch>& matches() const { return matches_; }

  const std::vector<ConstBufferView>& separators() const { return separators_; }

  size_t num_identical() const { return num_identical_; }

 protected:
  // Post-processes |matches_| to remove potentially unfavorable entries.
  void Trim();

  // Populates |separators_| from |new_image_| and |matches_|.
  void GenerateSeparators(ConstBufferView new_image);

  // Storage of matched elements: A list of matched pairs, where the list of
  // "new" elements have increasing offsets and don't overlap. May be empty.
  std::vector<ElementMatch> matches_;

  // Storage of regions before / between (successive) / after |new_ensemble|
  // elements in |matches_|, including empty regions. Contains 1 more element
  // than |matches_|.
  std::vector<ConstBufferView> separators_;

  // Number of identical matches found in match candidates. These should be
  // excluded from |matches_|.
  size_t num_identical_ = 0;

 private:
  DISALLOW_COPY_AND_ASSIGN(EnsembleMatcher);
};

}  // namespace zucchini

#endif  // CHROME_INSTALLER_ZUCCHINI_ENSEMBLE_MATCHER_H_
