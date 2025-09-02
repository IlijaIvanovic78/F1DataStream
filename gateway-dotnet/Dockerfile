FROM mcr.microsoft.com/dotnet/sdk:8.0 AS build
WORKDIR /src


COPY telemetry.proto ./


COPY gateway-dotnet/gateway-dotnet.csproj ./gateway-dotnet/


RUN dotnet restore gateway-dotnet/gateway-dotnet.csproj


COPY gateway-dotnet/ ./gateway-dotnet/


RUN dotnet publish gateway-dotnet/gateway-dotnet.csproj -c Release -o /app


FROM mcr.microsoft.com/dotnet/aspnet:8.0
WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY --from=build /app ./
EXPOSE 8080
ENV ASPNETCORE_URLS=http://+:8080
ENTRYPOINT ["dotnet", "gateway-dotnet.dll"]
