// Copyright 2016 The Chromium Authors. All rights reserved.
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.

#include "modules/bluetooth/BluetoothAttributeInstanceMap.h"

#include "modules/bluetooth/BluetoothDevice.h"
#include "modules/bluetooth/BluetoothRemoteGATTService.h"
#include <memory>
#include <utility>

namespace blink {

BluetoothAttributeInstanceMap::BluetoothAttributeInstanceMap(
    BluetoothDevice* device)
    : device_(device) {}

BluetoothRemoteGATTService*
BluetoothAttributeInstanceMap::GetOrCreateRemoteGATTService(
    mojom::blink::WebBluetoothRemoteGATTServicePtr remote_gatt_service,
    bool is_primary,
    const String& device_instance_id) {
  String service_instance_id = remote_gatt_service->instance_id;
  BluetoothRemoteGATTService* service =
      service_id_to_object_.at(service_instance_id);

  if (!service) {
    service =
        new BluetoothRemoteGATTService(std::move(remote_gatt_service),
                                       is_primary, device_instance_id, device_);
    service_id_to_object_.insert(service_instance_id, service);
  }

  return service;
}

bool BluetoothAttributeInstanceMap::ContainsService(
    const String& service_instance_id) {
  return service_id_to_object_.Contains(service_instance_id);
}

BluetoothRemoteGATTCharacteristic*
BluetoothAttributeInstanceMap::GetOrCreateRemoteGATTCharacteristic(
    ExecutionContext* context,
    mojom::blink::WebBluetoothRemoteGATTCharacteristicPtr
        remote_gatt_characteristic,
    BluetoothRemoteGATTService* service) {
  String instance_id = remote_gatt_characteristic->instance_id;
  BluetoothRemoteGATTCharacteristic* characteristic =
      characteristic_id_to_object_.at(instance_id);

  if (!characteristic) {
    characteristic = BluetoothRemoteGATTCharacteristic::Create(
        context, std::move(remote_gatt_characteristic), service, device_);
    characteristic_id_to_object_.insert(instance_id, characteristic);
  }

  return characteristic;
}

bool BluetoothAttributeInstanceMap::ContainsCharacteristic(
    const String& characteristic_instance_id) {
  return characteristic_id_to_object_.Contains(characteristic_instance_id);
}

BluetoothRemoteGATTDescriptor*
BluetoothAttributeInstanceMap::GetOrCreateBluetoothRemoteGATTDescriptor(
    mojom::blink::WebBluetoothRemoteGATTDescriptorPtr descriptor,
    BluetoothRemoteGATTCharacteristic* characteristic) {
  String instance_id = descriptor->instance_id;
  BluetoothRemoteGATTDescriptor* result =
      descriptor_id_to_object_.at(instance_id);

  if (result)
    return result;

  result =
      new BluetoothRemoteGATTDescriptor(std::move(descriptor), characteristic);
  descriptor_id_to_object_.insert(instance_id, result);
  return result;
}

bool BluetoothAttributeInstanceMap::ContainsDescriptor(
    const String& descriptor_instance_id) {
  return descriptor_id_to_object_.Contains(descriptor_instance_id);
}

void BluetoothAttributeInstanceMap::Clear() {
  service_id_to_object_.clear();
  characteristic_id_to_object_.clear();
  descriptor_id_to_object_.clear();
}

void BluetoothAttributeInstanceMap::Trace(blink::Visitor* visitor) {
  visitor->Trace(device_);
  visitor->Trace(service_id_to_object_);
  visitor->Trace(characteristic_id_to_object_);
  visitor->Trace(descriptor_id_to_object_);
}

}  // namespace blink
