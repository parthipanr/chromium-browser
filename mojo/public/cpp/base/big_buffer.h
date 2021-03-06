// Copyright 2018 The Chromium Authors. All rights reserved.
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.

#ifndef MOJO_PUBLIC_CPP_BASE_BIG_BUFFER_H_
#define MOJO_PUBLIC_CPP_BASE_BIG_BUFFER_H_

#include <cstdint>
#include <vector>

#include "base/containers/span.h"
#include "base/macros.h"
#include "base/optional.h"
#include "mojo/public/cpp/base/mojo_base_export.h"
#include "mojo/public/cpp/bindings/struct_traits.h"
#include "mojo/public/cpp/system/buffer.h"

namespace mojo_base {

class BigBuffer;

namespace internal {

// Internal helper used by BigBuffer when backed by shared memory.
class MOJO_BASE_EXPORT BigBufferSharedMemoryRegion {
 public:
  BigBufferSharedMemoryRegion();
  BigBufferSharedMemoryRegion(mojo::ScopedSharedBufferHandle buffer_handle,
                              size_t size);
  BigBufferSharedMemoryRegion(BigBufferSharedMemoryRegion&& other);
  ~BigBufferSharedMemoryRegion();

  BigBufferSharedMemoryRegion& operator=(BigBufferSharedMemoryRegion&& other);

  void* memory() const { return buffer_mapping_.get(); }

  size_t size() const { return size_; }
  mojo::ScopedSharedBufferHandle TakeBufferHandle();

 private:
  friend class mojo_base::BigBuffer;

  size_t size_;
  mojo::ScopedSharedBufferHandle buffer_handle_;
  mojo::ScopedSharedBufferMapping buffer_mapping_;

  DISALLOW_COPY_AND_ASSIGN(BigBufferSharedMemoryRegion);
};

}  // namespace internal

// BigBuffer represents a potentially large sequence of bytes. When passed over
// mojom (as a mojo_base::mojom::BigBuffer union), it may serialize as either an
// inlined array of bytes or as a shared buffer handle with the payload copied
// into the corresponding shared memory region. This makes it easier to send
// payloads of varying and unbounded size over IPC without fear of hitting
// message size limits.
//
// A BigBuffer may be (implicitly) constructed over any span of bytes, and it
// exposes simple |data()| and |size()| accessors akin to what common container
// types provide. Users do not need to be concerned with the actual backing
// storage used to implement this interface.
class MOJO_BASE_EXPORT BigBuffer {
 public:
  static constexpr size_t kMaxInlineBytes = 64 * 1024;

  enum class StorageType {
    kBytes,
    kSharedMemory,
  };

  // Defaults to empty vector storage.
  BigBuffer();
  BigBuffer(BigBuffer&& other);

  // Constructs a BigBuffer over an existing span of bytes. Intentionally
  // implicit for convenience. Always copies the contents of |data| into some
  // internal storage.
  BigBuffer(base::span<const uint8_t> data);

  // Helper for implicit conversion from byte vectors.
  BigBuffer(const std::vector<uint8_t>& data);

  // Constructs a BigBuffer from an existing shared memory region. Not intended
  // for general-purpose use.
  explicit BigBuffer(internal::BigBufferSharedMemoryRegion shared_memory);

  ~BigBuffer();

  BigBuffer& operator=(BigBuffer&& other);

  // Returns a pointer to the data stored by this BigBuffer, regardless of
  // backing storage type.
  uint8_t* data();
  const uint8_t* data() const;

  // Returns the size of the data stored by this BigBuffer, regardless of
  // backing storage type.
  size_t size() const;

  StorageType storage_type() const { return storage_type_; }

  const std::vector<uint8_t>& bytes() const {
    DCHECK_EQ(storage_type_, StorageType::kBytes);
    return bytes_;
  }

  internal::BigBufferSharedMemoryRegion& shared_memory() {
    DCHECK_EQ(storage_type_, StorageType::kSharedMemory);
    return shared_memory_.value();
  }

 private:
  StorageType storage_type_;
  std::vector<uint8_t> bytes_;
  base::Optional<internal::BigBufferSharedMemoryRegion> shared_memory_;

  DISALLOW_COPY_AND_ASSIGN(BigBuffer);
};

}  // namespace mojo_base

#endif  // MOJO_PUBLIC_CPP_BASE_BIG_BUFFER_H_
