# Native unit tests for firmware helpers (host g++, no Arduino SDK required).

CXX ?= g++
CXXFLAGS ?= -std=c++17 -Wall -Wextra -Werror -I../arduinoLuna

.PHONY: test clean

TEST_BIN := test_encoder_quadrature_runner

test: $(TEST_BIN)
	./$(TEST_BIN)

$(TEST_BIN): test_encoder_quadrature.cpp ../arduinoLuna/encoder_quadrature.h
	$(CXX) $(CXXFLAGS) -o $(TEST_BIN) test_encoder_quadrature.cpp

clean:
	rm -f $(TEST_BIN)
