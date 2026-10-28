# Ada URL

The package uses the common ada-idna library instead of the bundled IDNA
amalgamation. Its production build keeps upstream's default regex provider
configuration. To run upstream tests, use a separate work directory and pass
`ADA_PORTS_TESTING=ON` to the normal pkgsrc `test` target; this builds the
upstream test configuration, including its test-only std::regex provider.
Do not package that test build as the production library.
