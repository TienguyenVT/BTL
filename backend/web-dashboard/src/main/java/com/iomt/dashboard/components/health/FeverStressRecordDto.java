package com.iomt.dashboard.components.health;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.List;

@Data
@NoArgsConstructor
@AllArgsConstructor
public class FeverStressRecordDto {

    public List<SessionDto.HealthRecordDto> records;

    public long totalCount;

    public int page;

    public int size;

    public int totalPages;
}
