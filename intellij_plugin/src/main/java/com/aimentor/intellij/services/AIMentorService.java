package com.aimentor.intellij.services;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.intellij.openapi.application.ApplicationManager;
import com.intellij.openapi.components.Service;
import com.intellij.openapi.diagnostic.Logger;
import com.intellij.openapi.project.Project;
import com.intellij.notification.Notification;
import com.intellij.notification.NotificationType;
import com.intellij.notification.Notifications;
import org.apache.http.HttpResponse;
import org.apache.http.client.HttpClient;
import org.apache.http.client.methods.HttpGet;
import org.apache.http.client.methods.HttpPost;
import org.apache.http.entity.StringEntity;
import org.apache.http.impl.client.HttpClientBuilder;
import org.apache.http.util.EntityUtils;
import org.jetbrains.annotations.NotNull;
import org.jetbrains.annotations.Nullable;

import java.io.IOException;
import java.util.HashMap;
import java.util.Map;
import java.util.concurrent.CompletableFuture;

/**
 * Core service for AI Mentor functionality in IntelliJ IDEA
 * Handles communication with the AI Mentor backend service
 */
@Service
public final class AIMentorService {
    
    private static final Logger LOG = Logger.getInstance(AIMentorService.class);
    private static final String DEFAULT_SERVICE_URL = "http://localhost:8081";
    
    private final HttpClient httpClient;
    private final ObjectMapper objectMapper;
    private String serviceUrl;
    private String currentSessionId;
    private Project project;
    
    // Meeting context
    private boolean isInMeeting = false;
    private String currentMeetingId;
    private Map<String, Object> meetingContext;
    
    // Jira integration
    private String currentJiraTask;
    private Map<String, Object> jiraContext;
    
    public AIMentorService() {
        this.httpClient = HttpClientBuilder.create().build();
        this.objectMapper = new ObjectMapper();
        this.serviceUrl = System.getProperty("aimentor.service.url", DEFAULT_SERVICE_URL);
        this.meetingContext = new HashMap<>();
        this.jiraContext = new HashMap<>();
    }
    
    public void setProject(@NotNull Project project) {
        this.project = project;
    }
    
    /**
     * Initialize connection to AI Mentor service
     */
    public CompletableFuture<Boolean> initialize() {
        return CompletableFuture.supplyAsync(() -> {
            try {
                HttpGet request = new HttpGet(serviceUrl + "/api/health");
                HttpResponse response = httpClient.execute(request);
                
                if (response.getStatusLine().getStatusCode() == 200) {
                    LOG.info("AI Mentor service connected successfully");
                    showNotification("AI Mentor connected", "Ready to assist with your coding!", NotificationType.INFORMATION);
                    return true;
                } else {
                    LOG.warn("AI Mentor service not available at " + serviceUrl);
                    return false;
                }
            } catch (IOException e) {
                LOG.error("Failed to connect to AI Mentor service", e);
                showNotification("AI Mentor connection failed", "Service not available", NotificationType.WARNING);
                return false;
            }
        });
    }
    
    /**
     * Ask AI Mentor a question about code or current task
     */
    public CompletableFuture<String> askQuestion(@NotNull String question, @Nullable String selectedCode, @Nullable String fileName) {
        return CompletableFuture.supplyAsync(() -> {
            try {
                Map<String, Object> requestData = new HashMap<>();
                requestData.put("question", question);
                requestData.put("code", selectedCode);
                requestData.put("file_name", fileName);
                requestData.put("meeting_context", meetingContext);
                requestData.put("jira_context", jiraContext);
                requestData.put("project_name", project != null ? project.getName() : "unknown");
                
                String jsonRequest = objectMapper.writeValueAsString(requestData);
                
                HttpPost request = new HttpPost(serviceUrl + "/api/ask");
                request.setHeader("Content-Type", "application/json");
                request.setEntity(new StringEntity(jsonRequest));
                
                HttpResponse response = httpClient.execute(request);
                String responseBody = EntityUtils.toString(response.getEntity());
                
                if (response.getStatusLine().getStatusCode() == 200) {
                    JsonNode jsonResponse = objectMapper.readTree(responseBody);
                    return jsonResponse.get("answer").asText();
                } else {
                    LOG.warn("AI Mentor request failed: " + responseBody);
                    return "Sorry, I couldn't process your question. Please try again.";
                }
                
            } catch (Exception e) {
                LOG.error("Failed to ask AI Mentor question", e);
                return "Error occurred while processing your question.";
            }
        });
    }
    
    /**
     * Analyze selected code with AI Mentor
     */
    public CompletableFuture<String> analyzeCode(@NotNull String code, @NotNull String language, @Nullable String fileName) {
        return CompletableFuture.supplyAsync(() -> {
            try {
                Map<String, Object> requestData = new HashMap<>();
                requestData.put("code", code);
                requestData.put("language", language);
                requestData.put("file_name", fileName);
                requestData.put("analysis_type", "comprehensive");
                requestData.put("context", jiraContext);
                
                String jsonRequest = objectMapper.writeValueAsString(requestData);
                
                HttpPost request = new HttpPost(serviceUrl + "/api/analyze");
                request.setHeader("Content-Type", "application/json");
                request.setEntity(new StringEntity(jsonRequest));
                
                HttpResponse response = httpClient.execute(request);
                String responseBody = EntityUtils.toString(response.getEntity());
                
                if (response.getStatusLine().getStatusCode() == 200) {
                    JsonNode jsonResponse = objectMapper.readTree(responseBody);
                    return jsonResponse.get("analysis").asText();
                } else {
                    return "Failed to analyze code: " + responseBody;
                }
                
            } catch (Exception e) {
                LOG.error("Failed to analyze code", e);
                return "Error occurred during code analysis.";
            }
        });
    }
    
    /**
     * Generate code based on current Jira task
     */
    public CompletableFuture<String> generateCodeForTask(@NotNull String taskDescription, @NotNull String language) {
        return CompletableFuture.supplyAsync(() -> {
            try {
                Map<String, Object> requestData = new HashMap<>();
                requestData.put("task", taskDescription);
                requestData.put("language", language);
                requestData.put("jira_task", currentJiraTask);
                requestData.put("meeting_context", meetingContext);
                requestData.put("project_context", getProjectContext());
                
                String jsonRequest = objectMapper.writeValueAsString(requestData);
                
                HttpPost request = new HttpPost(serviceUrl + "/api/generate");
                request.setHeader("Content-Type", "application/json");
                request.setEntity(new StringEntity(jsonRequest));
                
                HttpResponse response = httpClient.execute(request);
                String responseBody = EntityUtils.toString(response.getEntity());
                
                if (response.getStatusLine().getStatusCode() == 200) {
                    JsonNode jsonResponse = objectMapper.readTree(responseBody);
                    return jsonResponse.get("code").asText();
                } else {
                    return "// Failed to generate code: " + responseBody;
                }
                
            } catch (Exception e) {
                LOG.error("Failed to generate code", e);
                return "// Error occurred during code generation";
            }
        });
    }
    
    /**
     * Sync with Jira tasks
     */
    public CompletableFuture<Map<String, Object>> syncJiraTasks() {
        return CompletableFuture.supplyAsync(() -> {
            try {
                HttpGet request = new HttpGet(serviceUrl + "/api/jira/tasks");
                HttpResponse response = httpClient.execute(request);
                String responseBody = EntityUtils.toString(response.getEntity());
                
                if (response.getStatusLine().getStatusCode() == 200) {
                    JsonNode jsonResponse = objectMapper.readTree(responseBody);
                    Map<String, Object> result = objectMapper.convertValue(jsonResponse, Map.class);
                    
                    // Update current context if tasks are available
                    if (result.containsKey("tasks")) {
                        updateJiraContext(result);
                    }
                    
                    return result;
                } else {
                    Map<String, Object> errorResult = new HashMap<>();
                    errorResult.put("error", "Failed to sync Jira tasks");
                    return errorResult;
                }
                
            } catch (Exception e) {
                LOG.error("Failed to sync Jira tasks", e);
                Map<String, Object> errorResult = new HashMap<>();
                errorResult.put("error", e.getMessage());
                return errorResult;
            }
        });
    }
    
    /**
     * Update meeting context when user joins a meeting
     */
    public void updateMeetingContext(@NotNull String meetingId, @NotNull Map<String, Object> context) {
        this.isInMeeting = true;
        this.currentMeetingId = meetingId;
        this.meetingContext.clear();
        this.meetingContext.putAll(context);
        
        LOG.info("Meeting context updated: " + meetingId);
        showNotification("Meeting Detected", "AI Mentor is now aware of your meeting context", NotificationType.INFORMATION);
    }
    
    /**
     * Clear meeting context when user leaves meeting
     */
    public void clearMeetingContext() {
        this.isInMeeting = false;
        this.currentMeetingId = null;
        this.meetingContext.clear();
        
        LOG.info("Meeting context cleared");
    }
    
    /**
     * Update Jira context
     */
    private void updateJiraContext(Map<String, Object> jiraData) {
        this.jiraContext.clear();
        this.jiraContext.putAll(jiraData);
        
        // Set current task if available
        if (jiraData.containsKey("current_task")) {
            this.currentJiraTask = jiraData.get("current_task").toString();
        }
    }
    
    /**
     * Get current project context
     */
    private Map<String, Object> getProjectContext() {
        Map<String, Object> context = new HashMap<>();
        
        if (project != null) {
            context.put("name", project.getName());
            context.put("base_path", project.getBasePath());
            context.put("is_open", !project.isDisposed());
        }
        
        return context;
    }
    
    /**
     * Show notification to user
     */
    private void showNotification(@NotNull String title, @NotNull String content, @NotNull NotificationType type) {
        ApplicationManager.getApplication().invokeLater(() -> {
            Notification notification = new Notification(
                "AI Mentor",
                title,
                content,
                type
            );
            Notifications.Bus.notify(notification, project);
        });
    }
    
    // Getters for current state
    public boolean isInMeeting() {
        return isInMeeting;
    }
    
    public String getCurrentMeetingId() {
        return currentMeetingId;
    }
    
    public String getCurrentJiraTask() {
        return currentJiraTask;
    }
    
    public Map<String, Object> getMeetingContext() {
        return new HashMap<>(meetingContext);
    }
    
    public Map<String, Object> getJiraContext() {
        return new HashMap<>(jiraContext);
    }
}
