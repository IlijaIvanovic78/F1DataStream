using Microsoft.AspNetCore.Mvc;
using Telemetry;
using Google.Protobuf.WellKnownTypes;
using System.ComponentModel.DataAnnotations;

namespace gateway_dotnet.Controllers;

/// <summary>
/// Data transfer object for telemetry responses
/// </summary>
/// <param name="Id">Unique identifier for the telemetry record</param>
/// <param name="Driver">Name of the driver</param>
/// <param name="TimestampUtc">UTC timestamp of the telemetry measurement</param>
/// <param name="LapNumber">Lap number during which the telemetry was recorded</param>
/// <param name="X">X coordinate position</param>
/// <param name="Y">Y coordinate position</param>
/// <param name="Speed">Current speed in km/h</param>
/// <param name="Throttle">Throttle position as percentage (0-100)</param>
/// <param name="Brake">Whether brake is applied</param>
/// <param name="NGear">Current gear number</param>
/// <param name="Rpm">Engine RPM</param>
/// <param name="Drs">Whether DRS (Drag Reduction System) is active</param>
public record TelemetryDto(long Id, string Driver, DateTime TimestampUtc, int LapNumber, double X, double Y, double Speed, double Throttle, bool Brake, int NGear, double Rpm, bool Drs);

/// <summary>
/// Data transfer object for creating new telemetry records
/// </summary>
/// <param name="Driver">Name of the driver</param>
/// <param name="TimestampUtc">UTC timestamp of the telemetry measurement</param>
/// <param name="LapNumber">Lap number during which the telemetry was recorded</param>
/// <param name="X">X coordinate position</param>
/// <param name="Y">Y coordinate position</param>
/// <param name="Speed">Current speed in km/h</param>
/// <param name="Throttle">Throttle position as percentage (0-100)</param>
/// <param name="Brake">Whether brake is applied</param>
/// <param name="NGear">Current gear number</param>
/// <param name="Rpm">Engine RPM</param>
/// <param name="Drs">Whether DRS (Drag Reduction System) is active</param>
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

/// <summary>
/// Data transfer object for updating telemetry records
/// </summary>
/// <param name="Driver">Name of the driver</param>
/// <param name="TimestampUtc">UTC timestamp of the telemetry measurement</param>
/// <param name="LapNumber">Lap number during which the telemetry was recorded</param>
/// <param name="X">X coordinate position</param>
/// <param name="Y">Y coordinate position</param>
/// <param name="Speed">Current speed in km/h</param>
/// <param name="Throttle">Throttle position as percentage (0-100)</param>
/// <param name="Brake">Whether brake is applied</param>
/// <param name="NGear">Current gear number</param>
/// <param name="Rpm">Engine RPM</param>
/// <param name="Drs">Whether DRS (Drag Reduction System) is active</param>
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

    /// <summary>
    /// Initializes a new instance of the TelemetryController
    /// </summary>
    /// <param name="client">gRPC client for telemetry service</param>
    public TelemetryController(TelemetryService.TelemetryServiceClient client)
    {
        _client = client;
    }

    // Helper methods for conversions
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

    /// <summary>
    /// Retrieves a paginated list of telemetry records with optional filtering
    /// </summary>
    /// <param name="driver">Optional filter by driver name</param>
    /// <param name="lap">Optional filter by lap number</param>
    /// <param name="page">Page number (default: 1)</param>
    /// <param name="pageSize">Number of items per page (default: 50, max: 100)</param>
    /// <returns>Paginated telemetry records</returns>
    /// <response code="200">Returns the paginated telemetry data</response>
    /// <response code="400">Invalid query parameters</response>
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

    /// <summary>
    /// Retrieves a specific telemetry record by ID
    /// </summary>
    /// <param name="id">The ID of the telemetry record</param>
    /// <returns>The telemetry record</returns>
    /// <response code="200">Returns the telemetry record</response>
    /// <response code="404">Telemetry record not found</response>
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

    /// <summary>
    /// Creates a new telemetry record
    /// </summary>
    /// <param name="dto">The telemetry data to create</param>
    /// <returns>The created telemetry record</returns>
    /// <response code="201">Telemetry record created successfully</response>
    /// <response code="400">Invalid input data</response>
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

    /// <summary>
    /// Updates an existing telemetry record
    /// </summary>
    /// <param name="id">The ID of the telemetry record to update</param>
    /// <param name="dto">The updated telemetry data</param>
    /// <returns>The updated telemetry record</returns>
    /// <response code="200">Telemetry record updated successfully</response>
    /// <response code="400">Invalid input data</response>
    /// <response code="404">Telemetry record not found</response>
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

    /// <summary>
    /// Deletes a telemetry record
    /// </summary>
    /// <param name="id">The ID of the telemetry record to delete</param>
    /// <returns>No content if successful</returns>
    /// <response code="204">Telemetry record deleted successfully</response>
    /// <response code="404">Telemetry record not found</response>
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

    /// <summary>
    /// Performs aggregation calculations on telemetry data
    /// </summary>
    /// <param name="field">The field to aggregate (SPEED, RPM, THROTTLE, X, Y)</param>
    /// <param name="type">The aggregation type (MIN, MAX, AVG, SUM)</param>
    /// <param name="driver">Optional filter by driver name</param>
    /// <param name="lap">Optional filter by lap number</param>
    /// <param name="from">Optional start time filter</param>
    /// <param name="to">Optional end time filter</param>
    /// <returns>Aggregation result</returns>
    /// <response code="200">Returns the aggregation result</response>
    /// <response code="400">Invalid aggregation parameters</response>
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