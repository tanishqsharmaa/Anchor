"use client";

import { useState, useEffect, useCallback } from "react";

export interface QueryHistoryItem {
  id: string;
  query: string;
  timestamp: string;
  answer?: string;
  routeType?: string;
  status?: "completed" | "abstained" | "error";
}

const STORAGE_KEY = "anchor_query_history_v1";
const MAX_HISTORY_ITEMS = 50;

export function useQueryHistory() {
  const [history, setHistory] = useState<QueryHistoryItem[]>([]);

  // Load from localStorage on mount
  useEffect(() => {
    try {
      const stored = localStorage.getItem(STORAGE_KEY);
      if (stored) {
        setHistory(JSON.parse(stored));
      }
    } catch (e) {
      console.warn("Failed to load query history from localStorage:", e);
    }
  }, []);

  const saveHistory = useCallback((items: QueryHistoryItem[]) => {
    setHistory(items);
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(items));
    } catch (e) {
      console.warn("Failed to persist query history:", e);
    }
  }, []);

  const addQuery = useCallback(
    (item: Omit<QueryHistoryItem, "id" | "timestamp"> & { id?: string; timestamp?: string }) => {
      const newItem: QueryHistoryItem = {
        id: item.id || `hist_${Date.now()}`,
        query: item.query,
        timestamp: item.timestamp || new Date().toISOString(),
        answer: item.answer,
        routeType: item.routeType,
        status: item.status || "completed",
      };

      setHistory((prev) => {
        // Deduplicate recent identical query if present
        const filtered = prev.filter((p) => p.query !== item.query);
        const updated = [newItem, ...filtered].slice(0, MAX_HISTORY_ITEMS);
        try {
          localStorage.setItem(STORAGE_KEY, JSON.stringify(updated));
        } catch (e) {
          console.warn("Failed to persist query history:", e);
        }
        return updated;
      });
    },
    []
  );

  const removeQuery = useCallback(
    (id: string) => {
      setHistory((prev) => {
        const updated = prev.filter((item) => item.id !== id);
        try {
          localStorage.setItem(STORAGE_KEY, JSON.stringify(updated));
        } catch (e) {
          console.warn("Failed to update query history:", e);
        }
        return updated;
      });
    },
    []
  );

  const clearHistory = useCallback(() => {
    setHistory([]);
    try {
      localStorage.removeItem(STORAGE_KEY);
    } catch (e) {
      console.warn("Failed to clear query history:", e);
    }
  }, []);

  return {
    history,
    addQuery,
    removeQuery,
    clearHistory,
  };
}
