package com.iomt.dashboard.components.device;

/**
 * ============================================================
 * DeviceController — REST Controller: Quan ly thiet bi
 * ============================================================
 *
 * BASE PATH: /api/devices
 * SECURITY:  Protected (can JWT)
 *
 * ENDPOINTS:
 *
 *    POST /api/devices
 *       Them thiet bi moi.
 *       INPUT : { macAddress, name }
 *       OUTPUT: 201 + DeviceDto | 409 (MAC da ton tai)
 *
 *    GET /api/devices
 *       Lay danh sach thiet bi.
 *       OUTPUT: 200 + List<DeviceDto>
 *
 *    DELETE /api/devices/{id}
 *       Xoa thiet bi.
 *       OUTPUT: 204 | 404
 */
public class DeviceController {

    // ----------------------------------------------------------
    // POST /api/devices
    //    @PostMapping
    //    public ResponseEntity<DeviceDto> create(@RequestBody DeviceDto dto) {
    //        DeviceDto created = deviceService.create(getCurrentUserId(), dto);
    //        return ResponseEntity.status(HttpStatus.CREATED).body(created);
    //    }
    // ----------------------------------------------------------

    // ----------------------------------------------------------
    // GET /api/devices
    //    @GetMapping
    //    public ResponseEntity<List<DeviceDto>> getAll() {
    //        return ResponseEntity.ok(deviceService.getAll(getCurrentUserId()));
    //    }
    // ----------------------------------------------------------

    // ----------------------------------------------------------
    // DELETE /api/devices/{id}
    //    @DeleteMapping("/{id}")
    //    public ResponseEntity<Void> delete(@PathVariable String id) {
    //        deviceService.delete(id, getCurrentUserId());
    //        return ResponseEntity.noContent().build();
    //    }
    // ----------------------------------------------------------
}
