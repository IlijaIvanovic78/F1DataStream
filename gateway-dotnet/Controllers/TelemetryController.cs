using Microsoft.AspNetCore.Mvc;
using Telemetry;
using Google.Protobuf.WellKnownTypes;
using System.ComponentModel.DataAnnotations;

namespace gateway_dotnet.Controllers;

public record TelemetryDto(long Id, string Driver, DateTime TimestampUtc, int LapNumber, double X, double Y, double Speed, double Throttle, bool Brake, int NGear, double Rpm, bool Drs);

public record CreateTelemetryDto(
    [Required][MaxLength(100)] string Driver,
    [Required] DateTime TimestampUtc,
    [Required][Range(1, 100)] int LapNumber,
    [Required] double X,
    [Required] double Y,
    [Required][Range(0, 400)] double Speed,
    [Required][Range(0, 100)] double Throttle,
    [Required] bool Brake,
    [Required][Range(-1, 8)] int NGear,
    [Required][Range(0, 20000)] double Rpm,
    [Required] bool Drs
);

public record UpdateTelemetryDto(
    [Required][MaxLength(100)] string Driver,
    [Required] DateTime TimestampUtc,
    [Required][Range(1, 100)] int LapNumber,
    [Required] double X,
    [Required] double Y,
    [Required][Range(0, 400)] double Speed,
    [Required][Range(0, 100)] double Throttle,
    [Required] bool Brake,
    [Required][Range(-1, 8)] int NGear,
    [Required][Range(0, 20000)] double Rpm,
    [Required] bool Drs
);

/// <summary>
/// Telemetry API endpoints for managing racing telemetry data
/// </summary>
[ApiController]
[Route("api/[controller]")]
[Tags("Telemetry")]
public class TelemetryController : ControllerBase
{
    private readonly TelemetryService.TelemetryServiceClient _client;
    public TelemetryController(TelemetryService.TelemetryServiceClient client)
    {
        _client = client;
    }

    private static Timestamp DateTimeToTimestamp(DateTime dateTime)
    {
        return Timestamp.FromDateTime(DateTime.SpecifyKind(dateTime, DateTimeKind.Utc));
    }

    private static DateTime TimestampToDateTime(Timestamp timestamp)
    {
        return timestamp.ToDateTime();
    }

    private static TelemetryDto ToDto(Telemetry.Telemetry telemetry)
    {
        return new TelemetryDto(
            telemetry.Id,
            telemetry.Driver,
            TimestampToDateTime(telemetry.Timestamp),
            telemetry.LapNumber,
            telemetry.X,
            telemetry.Y,
            telemetry.Speed,
            telemetry.Throttle,
            telemetry.Brake,
            telemetry.NGear,
            telemetry.Rpm,
            telemetry.Drs
        );
    }

    private static Telemetry.Telemetry FromCreateDto(CreateTelemetryDto dto)
    {
        return new Telemetry.Telemetry
        {
            Driver = dto.Driver,
            Timestamp = DateTimeToTimestamp(dto.TimestampUtc),
            LapNumber = dto.LapNumber,
            X = dto.X,
            Y = dto.Y,
            Speed = dto.Speed,
            Throttle = dto.Throttle,
            Brake = dto.Brake,
            NGear = dto.NGear,
            Rpm = dto.Rpm,
            Drs = dto.Drs
        };
    }

    private static Telemetry.Telemetry FromUpdateDto(UpdateTelemetryDto dto, long id)
    {
        return new Telemetry.Telemetry
        {
            Id = id,
            Driver = dto.Driver,
            Timestamp = DateTimeToTimestamp(dto.TimestampUtc),
            LapNumber = dto.LapNumber,
            X = dto.X,
            Y = dto.Y,
            Speed = dto.Speed,
            Throttle = dto.Throttle,
            Brake = dto.Brake,
            NGear = dto.NGear,
            Rpm = dto.Rpm,
            Drs = dto.Drs
        };
    }

    private static AggregateField? ParseAggregateField(string? field)
    {
        return field?.ToUpperInvariant() switch
        {
            "SPEED" => AggregateField.Speed,
            "RPM" => AggregateField.Rpm,
            "THROTTLE" => AggregateField.Throttle,
            "X" => AggregateField.X,
            "Y" => AggregateField.Y,
            _ => null
        };
    }

    private static AggregateType? ParseAggregateType(string? type)
    {
        return type?.ToUpperInvariant() switch
        {
            "MIN" => AggregateType.Min,
            "MAX" => AggregateType.Max,
            "AVG" => AggregateType.Avg,
            "SUM" => AggregateType.Sum,
            _ => null
        };
    }

    [HttpGet]
    [ProducesResponseType(typeof(object), StatusCodes.Status200OK)]
    [ProducesResponseType(StatusCodes.Status400BadRequest)]
    public async Task<ActionResult<object>> GetTelemetries(
        [FromQuery] string? driver = null,
        [FromQuery] int? lap = null,
        [FromQuery][Range(1, int.MaxValue)] int page = 1,
        [FromQuery][Range(1, 100)] int pageSize = 50)
    {
        var request = new ListTelemetryRequest
        {
            Page = page,
            PageSize = pageSize,
            DriverFilter = driver ?? "",
            LapFilter = lap ?? 0
        };

        var response = await _client.ListTelemetryAsync(request);
        
        var telemetries = response.Telemetries.Select(ToDto).ToList();
        
        return Ok(new
        {
            telemetries,
            totalCount = response.TotalCount,
            page = response.Page,
            pageSize = response.PageSize,
            totalPages = response.TotalPages
        });
    }

    [HttpGet("{id:long}")]
    [ProducesResponseType(typeof(TelemetryDto), StatusCodes.Status200OK)]
    [ProducesResponseType(StatusCodes.Status404NotFound)]
    public async Task<ActionResult<TelemetryDto>> GetTelemetry([Range(1, long.MaxValue)] long id)
    {
        var request = new GetTelemetryRequest { Id = id };
        var response = await _client.GetTelemetryAsync(request);

        if (!response.Found)
        {
            return NotFound();
        }

        return Ok(ToDto(response.Telemetry));
    }

    [HttpPost]
    [ProducesResponseType(typeof(TelemetryDto), StatusCodes.Status201Created)]
    [ProducesResponseType(StatusCodes.Status400BadRequest)]
    public async Task<ActionResult<TelemetryDto>> CreateTelemetry([FromBody] CreateTelemetryDto dto)
    {
        var telemetry = FromCreateDto(dto);
        var request = new CreateTelemetryRequest { Telemetry = telemetry };
        
        var response = await _client.CreateTelemetryAsync(request);

        if (!response.Success)
        {
            return BadRequest(response.Message);
        }

        var result = ToDto(response.Telemetry);
        return CreatedAtAction(nameof(GetTelemetry), new { id = result.Id }, result);
    }

    [HttpPut("{id:long}")]
    [ProducesResponseType(typeof(TelemetryDto), StatusCodes.Status200OK)]
    [ProducesResponseType(StatusCodes.Status400BadRequest)]
    [ProducesResponseType(StatusCodes.Status404NotFound)]
    public async Task<ActionResult<TelemetryDto>> UpdateTelemetry([Range(1, long.MaxValue)] long id, [FromBody] UpdateTelemetryDto dto)
    {
        var telemetry = FromUpdateDto(dto, id);
        var request = new UpdateTelemetryRequest { Telemetry = telemetry };
        
        var response = await _client.UpdateTelemetryAsync(request);

        if (!response.Success)
        {
            return NotFound(response.Message);
        }

        return Ok(ToDto(response.Telemetry));
    }

    [HttpDelete("{id:long}")]
    [ProducesResponseType(StatusCodes.Status204NoContent)]
    [ProducesResponseType(StatusCodes.Status404NotFound)]
    public async Task<ActionResult> DeleteTelemetry([Range(1, long.MaxValue)] long id)
    {
        var request = new DeleteTelemetryRequest { Id = id };
        var response = await _client.DeleteTelemetryAsync(request);

        if (!response.Success)
        {
            return NotFound(response.Message);
        }

        return NoContent();
    }

    [HttpGet("aggregate")]
    [ProducesResponseType(typeof(object), StatusCodes.Status200OK)]
    [ProducesResponseType(StatusCodes.Status400BadRequest)]
    public async Task<ActionResult<object>> Aggregate(
        [FromQuery][Required] string field,
        [FromQuery][Required] string type,
        [FromQuery] string? driver = null,
        [FromQuery] int? lap = null,
        [FromQuery] DateTime? from = null,
        [FromQuery] DateTime? to = null)
    {
        var aggregateField = ParseAggregateField(field);
        var aggregateType = ParseAggregateType(type);

        if (!aggregateField.HasValue || !aggregateType.HasValue)
        {
            return BadRequest("Invalid field or type. Field must be one of: SPEED, RPM, THROTTLE, X, Y. Type must be one of: MIN, MAX, AVG, SUM.");
        }

        var request = new AggregateRequest
        {
            Field = aggregateField.Value,
            Type = aggregateType.Value,
            DriverFilter = driver ?? "",
            LapFilter = lap ?? 0
        };

        if (from.HasValue)
        {
            request.StartTime = DateTimeToTimestamp(from.Value);
        }

        if (to.HasValue)
        {
            request.EndTime = DateTimeToTimestamp(to.Value);
        }

        var response = await _client.AggregateAsync(request);

        if (!response.Success)
        {
            return BadRequest(response.Message);
        }

        return Ok(new
        {
            value = response.Value,
            count = response.Count,
            field = field.ToUpperInvariant(),
            type = type.ToUpperInvariant()
        });
    }
}