FROM maven:3.9-eclipse-temurin-21 AS build
WORKDIR /build

# Dependencies change less often than code; keep them in their own layer.
COPY pom.xml .
RUN mvn -q -B dependency:go-offline

COPY src ./src
RUN mvn -q -B -DskipTests package

FROM eclipse-temurin:21-jre
WORKDIR /app
COPY --from=build /build/target/stock-service-*.jar app.jar

RUN useradd --system --no-create-home app
USER app

EXPOSE 8081
# Size the heap from the container's memory limit instead of a fixed -Xmx.
ENTRYPOINT ["java", "-XX:MaxRAMPercentage=75", "-jar", "app.jar"]
