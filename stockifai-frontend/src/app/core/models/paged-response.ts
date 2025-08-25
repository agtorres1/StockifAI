export interface PagedResponse<T> {
  count: number;
  page: number;
  page_size: number;
  total_pages: number;
  results: T[];
}