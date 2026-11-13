import { downloadCsv, request } from './client';
import type { Benchmark, BenchmarkReport } from '../types/models';

export function listBenchmarks(): Promise<Benchmark[]> {
  return request<Benchmark[]>('/benchmarks');
}

export function getReport(id: number): Promise<BenchmarkReport> {
  return request<BenchmarkReport>(`/benchmarks/${id}`);
}

export function generate(city: string, functionType: string): Promise<Benchmark> {
  return request<Benchmark>('/benchmarks/generate', {
    method: 'POST',
    body: { city, function_type: functionType },
  });
}

export function publish(id: number): Promise<{ id: number; published: boolean }> {
  return request(`/benchmarks/${id}/publish`, { method: 'POST' });
}

export function exportBenchmark(id: number): Promise<void> {
  return downloadCsv(`/benchmarks/${id}/export.csv`, `jobnorm-benchmark-${id}.csv`);
}
