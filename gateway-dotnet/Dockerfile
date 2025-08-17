# Build stage
FROM mcr.microsoft.com/dotnet/sdk:8.0 AS build
WORKDIR /src

# Copy the proto file from parent directory
COPY telemetry.proto ./

# Copy project file
COPY gateway-dotnet/gateway-dotnet.csproj ./gateway-dotnet/

# Restore dependencies
RUN dotnet restore gateway-dotnet/gateway-dotnet.csproj

# Copy gateway source code
COPY gateway-dotnet/ ./gateway-dotnet/

# Build and publish
RUN dotnet publish gateway-dotnet/gateway-dotnet.csproj -c Release -o /app

# Runtime stage
FROM mcr.microsoft.com/dotnet/aspnet:8.0
WORKDIR /app

# >>> OVO JE BITNO: curl u RUNTIME fazi <<<
RUN apt-get update && apt-get install -y --no-install-recommends curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY --from=build /app ./
EXPOSE 8080
ENV ASPNETCORE_URLS=http://+:8080
ENTRYPOINT ["dotnet", "gateway-dotnet.dll"]
