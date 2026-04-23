# Language Test Tools Reference

Quick reference for test tools by programming language.

## Python

| Tool | Command | Config File | Notes |
|------|---------|-------------|-------|
| pytest | `pytest -v --tb=short` | `pytest.ini`, `pyproject.toml` | Most popular, recommended |
| unittest | `python -m unittest discover -v` | Built-in | Standard library |
| tox | `tox` | `tox.ini` | Multi-environment testing |
| nose2 | `nose2` | `unittest.cfg` | Successor to nose |

## Node.js

| Tool | Command | Config File | Notes |
|------|---------|-------------|-------|
| jest | `jest` | `jest.config.js` | Facebook, very popular |
| vitest | `vitest` | `vitest.config.ts` | Vite-native, fast |
| mocha | `mocha` | `.mocharc.js` | Flexible, mature |
| cypress | `cypress run` | `cypress.config.js` | E2E testing |
| playwright | `playwright test` | `playwright.config.ts` | Microsoft E2E |

## Go

| Tool | Command | Notes |
|------|---------|-------|
| go test | `go test -v ./...` | Built-in, no config needed |

## Rust

| Tool | Command | Notes |
|------|---------|-------|
| cargo test | `cargo test` | Built-in, integrates with crates |

## Java

| Tool | Command | Config File | Notes |
|------|---------|-------------|-------|
| Maven | `mvn test` | `pom.xml` | Industry standard |
| Gradle | `gradle test` / `./gradlew test` | `build.gradle` | Flexible, fast |
| JUnit | Via Maven/Gradle | - | De facto standard |

## Ruby

| Tool | Command | Notes |
|------|---------|-------|
| RSpec | `rspec` or `bundle exec rspec` | BDD style |
| Minitest | `ruby -Itest` | Built-in, simple |

## PHP

| Tool | Command | Config File | Notes |
|------|---------|-------------|-------|
| PHPUnit | `phpunit` or `vendor/bin/phpunit` | `phpunit.xml` | De facto standard |

## C# / .NET

| Tool | Command | Notes |
|------|---------|-------|
| dotnet test | `dotnet test` | Built-in CLI |

## Swift

| Tool | Command | Notes |
|------|---------|-------|
| XCTest | `swift test` | Built-in |

## Kotlin

| Tool | Command | Notes |
|------|---------|-------|
| JUnit (via Gradle) | `./gradlew test` | Standard JVM |
