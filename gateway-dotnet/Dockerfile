# Build stage
FROM mcr.microsoft.com/dotnet/sdk:9.0 AS build
WORKDIR /src

# Kopiraj csproj i restore
COPY *.csproj ./
RUN dotnet restore

# Kopiraj ostalo i build
COPY . .
RUN dotnet publish -c Release -o /app/publish

# Runtime stage
FROM mcr.microsoft.com/dotnet/aspnet:9.0 AS final
WORKDIR /app
COPY --from=build /app/publish .
# Optional: EXPOSE 8080
ENTRYPOINT ["dotnet", "gateway-dotnet.dll"]
