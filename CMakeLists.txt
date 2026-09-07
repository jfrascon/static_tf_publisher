cmake_minimum_required(VERSION 3.8)
project(static_tf_publisher)

find_package(ament_cmake REQUIRED)
find_package(ament_cmake_python REQUIRED)

ament_python_install_package(${PROJECT_NAME})

install(
  DIRECTORY config docs launch
  DESTINATION share/${PROJECT_NAME}
  PATTERN "__pycache__" EXCLUDE
  PATTERN "*.pyc" EXCLUDE)

install(PROGRAMS scripts/static_tf_publisher_node DESTINATION lib/${PROJECT_NAME})

install(FILES README.md LICENSE DESTINATION share/${PROJECT_NAME})

if(BUILD_TESTING)
  find_package(ament_lint_auto REQUIRED)

  # Exclude linters that require package-specific configuration.
  list(APPEND AMENT_LINT_AUTO_EXCLUDE ament_cmake_flake8)

  # Register the remaining linters declared as test dependencies in package.xml.
  ament_lint_auto_find_test_dependencies()

  find_package(ament_cmake_flake8 REQUIRED)

  ament_flake8(CONFIG_FILE "${CMAKE_CURRENT_SOURCE_DIR}/ament_flake8.ini")

  ament_add_pytest_test(test_frame_config tests/test_frame_config.py TIMEOUT 120)
  ament_add_pytest_test(
    test_installation tests/test_installation.py TIMEOUT 120 ENV
    "AMENT_PREFIX_PATH=${CMAKE_INSTALL_PREFIX}:$ENV{AMENT_PREFIX_PATH}")
  ament_add_pytest_test(test_launch_contract tests/test_launch_contract.py TIMEOUT 120)
  ament_add_pytest_test(test_launch_smoke tests/test_launch_smoke.py TIMEOUT 120)
  ament_add_pytest_test(test_launch_utils tests/test_launch_utils.py TIMEOUT 120)
endif()

ament_package()
