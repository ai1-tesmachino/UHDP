import api from "./client";

export interface SyncStatus {
    enabled: boolean;
    states: {
        Pending: number;
        Syncing: number;
        Synced: number;
        "Needs attention": number;
    };
    last_successful_sync: string | null;
    failed_events: Array<{
        event_id: string;
        event_type: string;
        attempts: number;
        last_error: string | null;
    }>;
    cloud_configured: boolean;
}

export async function getSyncStatus() {
    const response = await api.get<SyncStatus>("/sync/status");
    return response.data;
}

export interface EntitySyncStatus {
    entity_type: string;
    entity_id: string;
    state: string;
    attempts: number;
    last_error: string | null;
    created_at: string | null;
    synced_at: string | null;
    cloud_configured: boolean;
}

export async function getEntitySyncStatus(entityType: string, entityId: string) {
    const response = await api.get<EntitySyncStatus>(
        `/sync/entity/${encodeURIComponent(entityType)}/${encodeURIComponent(entityId)}`,
    );
    return response.data;
}

export async function retrySync(eventId?: string) {
    const response = await api.post<{ retried: number }>("/sync/retry", {
        event_id: eventId ?? null,
    });
    return response.data;
}
