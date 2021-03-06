/*
 * Copyright (C) 2009 Google Inc. All rights reserved.
 *
 * Redistribution and use in source and binary forms, with or without
 * modification, are permitted provided that the following conditions are
 * met:
 *
 *     * Redistributions of source code must retain the above copyright
 * notice, this list of conditions and the following disclaimer.
 *     * Redistributions in binary form must reproduce the above
 * copyright notice, this list of conditions and the following disclaimer
 * in the documentation and/or other materials provided with the
 * distribution.
 *     * Neither the name of Google Inc. nor the names of its
 * contributors may be used to endorse or promote products derived from
 * this software without specific prior written permission.
 *
 * THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
 * "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
 * LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
 * A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
 * OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
 * SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
 * LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
 * DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
 * THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
 * (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
 * OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
 */

#include "platform/CrossThreadCopier.h"

#include <memory>
#include "platform/loader/fetch/ResourceError.h"
#include "platform/loader/fetch/ResourceRequest.h"
#include "platform/loader/fetch/ResourceResponse.h"
#include "platform/weborigin/KURL.h"
#include "platform/wtf/text/WTFString.h"

namespace blink {

CrossThreadCopier<KURL>::Type CrossThreadCopier<KURL>::Copy(const KURL& url) {
  return url.Copy();
}

CrossThreadCopier<String>::Type CrossThreadCopier<String>::Copy(
    const String& str) {
  return str.IsolatedCopy();
}

CrossThreadCopier<ResourceError>::Type CrossThreadCopier<ResourceError>::Copy(
    const ResourceError& error) {
  return error.Copy();
}

CrossThreadCopier<ResourceRequest>::Type
CrossThreadCopier<ResourceRequest>::Copy(const ResourceRequest& request) {
  return WTF::Passed(request.CopyData());
}

CrossThreadCopier<ResourceResponse>::Type
CrossThreadCopier<ResourceResponse>::Copy(const ResourceResponse& response) {
  return WTF::Passed(response.CopyData());
}

// Test CrossThreadCopier using static_assert.

// Verify that ThreadSafeRefCounted objects get handled correctly.
class CopierThreadSafeRefCountedTest
    : public ThreadSafeRefCounted<CopierThreadSafeRefCountedTest> {};

// Add a generic specialization which will let's us verify that no other
// template matches.
template <typename T>
struct CrossThreadCopierBase<T, false> {
  typedef int Type;
};

static_assert((std::is_same<scoped_refptr<CopierThreadSafeRefCountedTest>,
                            CrossThreadCopier<scoped_refptr<
                                CopierThreadSafeRefCountedTest>>::Type>::value),
              "RefPtr + ThreadSafeRefCounted should pass CrossThreadCopier");
static_assert(
    (std::is_same<
        int,
        CrossThreadCopier<CopierThreadSafeRefCountedTest*>::Type>::value),
    "Raw pointer + ThreadSafeRefCounted should NOT pass CrossThreadCopier");

// Verify that RefCounted objects only match our generic template which exposes
// Type as int.
class CopierRefCountedTest : public RefCounted<CopierRefCountedTest> {};

static_assert(
    (std::is_same<int, CrossThreadCopier<CopierRefCountedTest*>::Type>::value),
    "Raw pointer + RefCounted should NOT pass CrossThreadCopier");

// Verify that std::unique_ptr gets passed through.
static_assert(
    (std::is_same<std::unique_ptr<float>,
                  CrossThreadCopier<std::unique_ptr<float>>::Type>::value),
    "std::unique_ptr test");

}  // namespace blink
