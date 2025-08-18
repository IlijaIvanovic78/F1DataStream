using System.Net;
using System.Net.Http;
using System.Reflection;
using Microsoft.AspNetCore.Mvc;
using Telemetry;

var builder = WebApplication.CreateBuilder(args);

builder.WebHost.ConfigureKestrel(options =>
{
    options.ListenAnyIP(8080);
});

builder.Services.AddControllers().ConfigureApiBehaviorOptions(o =>
{
    o.InvalidModelStateResponseFactory = ctx =>
    {
        var problemDetails = new ValidationProblemDetails(ctx.ModelState);
        return new BadRequestObjectResult(problemDetails);
    };
});

// Swagger configuration
builder.Services.AddEndpointsApiExplorer();
builder.Services.AddSwaggerGen(c =>
{
    c.SwaggerDoc("v1", new()
    {
        Title = "Telemetry Gateway API",
        Version = "v1",
        Description = "REST API Gateway for IoT Racing Telemetry Data Management",
        Contact = new() { Name = "Telemetry Team" }
    });

    var xmlFilename = $"{Assembly.GetExecutingAssembly().GetName().Name}.xml";
    c.IncludeXmlComments(Path.Combine(AppContext.BaseDirectory, xmlFilename));

    c.TagActionsBy(api => new[] { api.GroupName ?? api.ActionDescriptor.RouteValues["controller"] });
    c.DocInclusionPredicate((name, api) => true);
});

// gRPC client configuration
AppContext.SetSwitch("System.Net.Http.SocketsHttpHandler.Http2UnencryptedSupport", true);
builder.Services.AddGrpcClient<TelemetryService.TelemetryServiceClient>(o =>
    o.Address = new Uri(builder.Configuration["Grpc:TelemetryServiceUrl"]!))
.ConfigurePrimaryHttpMessageHandler(() => new SocketsHttpHandler
{
    EnableMultipleHttp2Connections = true,
    AutomaticDecompression = DecompressionMethods.All
});

// Add Health Checks
builder.Services.AddHealthChecks();

var app = builder.Build();

if (app.Environment.IsDevelopment())
{
    app.UseSwagger();
    app.UseSwaggerUI(c =>
    {
        c.SwaggerEndpoint("/swagger/v1/swagger.json", "Telemetry Gateway API v1");
        c.RoutePrefix = string.Empty;
        c.DocumentTitle = "Telemetry Gateway API";
    });
}

app.UseHttpsRedirection();

app.MapControllers();

app.MapHealthChecks("/healthz");

app.Run();
