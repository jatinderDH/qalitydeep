"""JUnit XML output formatter for CI/CD integration."""
from __future__ import annotations
import xml.etree.ElementTree as ET
from datetime import datetime
from ..models import EvalRun, EvalCaseResult


class JUnitFormatter:
    def format_run(self, run: EvalRun, threshold: float = 0.5) -> str:
        """Generate JUnit XML from an eval run."""
        testsuites = ET.Element("testsuites")
        testsuites.set("name", f"QAlityDeep - {run.dataset_id}")
        testsuites.set("tests", str(len(run.cases)))

        failures = 0
        total_time = 0.0

        testsuite = ET.SubElement(testsuites, "testsuite")
        testsuite.set("name", run.dataset_id)
        testsuite.set("tests", str(len(run.cases)))
        testsuite.set("timestamp", run.created_at.isoformat())

        for case in run.cases:
            # Each metric becomes a testcase
            case_failed = False
            for metric_name, score in case.metrics.items():
                testcase = ET.SubElement(testsuite, "testcase")
                testcase.set("name", f"{case.test_case_id} - {metric_name}")
                testcase.set("classname", f"qalitydeep.{run.dataset_id}")

                latency = getattr(case, "latency_ms", None)
                if latency:
                    testcase.set("time", f"{latency / 1000:.3f}")
                    total_time += latency / 1000

                if score < threshold:
                    failure = ET.SubElement(testcase, "failure")
                    reason = case.metric_reasons.get(metric_name, "")
                    failure.set(
                        "message",
                        f"{metric_name} score {score:.3f} below threshold {threshold}",
                    )
                    failure.text = reason
                    if not case_failed:
                        failures += 1
                        case_failed = True

        testsuite.set("failures", str(failures))
        testsuite.set("time", f"{total_time:.3f}")
        testsuites.set("failures", str(failures))

        tree = ET.ElementTree(testsuites)
        ET.indent(tree, space="  ")

        return ET.tostring(
            testsuites, encoding="unicode", xml_declaration=True
        )

    def write_file(
        self, run: EvalRun, path: str, threshold: float = 0.5
    ) -> None:
        """Write JUnit XML to a file."""
        xml_content = self.format_run(run, threshold)
        with open(path, "w", encoding="utf-8") as f:
            f.write(xml_content)
