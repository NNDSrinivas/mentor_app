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
    private static final String DEFAULT_SERVICE_URL = "http://localhost:8084";
    
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
                Map<String, Object> payload = new HashMap<>();
                payload.put("question", question);
                // simple_web.py expects an optional 'context' object; include useful metadata
                Map<String, Object> context = new HashMap<>();
                if (fileName != null) context.put("file_name", fileName);
                if (selectedCode != null) context.put("selected_code", selectedCode);
                context.put("source", "intellij_plugin");
                payload.put("context", context);
                payload.put("interview_mode", false);

                String jsonRequest = objectMapper.writeValueAsString(payload);

                HttpPost request = new HttpPost(serviceUrl + "/api/ask");
                request.setHeader("Content-Type", "application/json");
                request.setEntity(new StringEntity(jsonRequest));
                
                HttpResponse response = httpClient.execute(request);
                String responseBody = EntityUtils.toString(response.getEntity());
                
                if (response.getStatusLine().getStatusCode() == 200) {
                    JsonNode jsonResponse = objectMapper.readTree(responseBody);
                    // simple_web responds with 'response'; fall back to 'answer' if present
                    if (jsonResponse.has("response")) {
                        return jsonResponse.get("response").asText();
                    } else if (jsonResponse.has("answer")) {
                        return jsonResponse.get("answer").asText();
                    }
                    return responseBody;
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
                // Route analysis through /api/ask with an analysis-style prompt
                StringBuilder sb = new StringBuilder();
                sb.append("Analyze the following ").append(language).append(" code and suggest improvements, potential bugs, refactorings, tests, and best practices.\n\n");
                if (fileName != null) {
                    sb.append("File: ").append(fileName).append("\n\n");
                }
                sb.append("Code:\n\n").append(code);

                return askQuestion(sb.toString(), code, fileName).get();
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
                StringBuilder sb = new StringBuilder();
                sb.append("Generate ").append(language).append(" code for the following task. ");
                if (currentJiraTask != null) sb.append("Related Jira task: ").append(currentJiraTask).append(". ");
                sb.append("Provide clean, correct code with comments if helpful.\n\n");
                sb.append("Task: ").append(taskDescription);

                return askQuestion(sb.toString(), null, null).get();
            } catch (Exception e) {
                LOG.error("Failed to generate code", e);
                return "// Error occurred during code generation";
            }
        });
    }

    /**
     * Overload used by GenerateCodeAction to include more preferences.
     */
    public CompletableFuture<String> generateCodeForTask(@NotNull String taskDescription,
                                                         @Nullable String fileName,
                                                         @Nullable String fileType,
                                                         @Nullable String existingCode,
                                                         @Nullable String codeStyle,
                                                         boolean includeTests) {
        String lang = fileType != null ? fileType : "plaintext";
        return CompletableFuture.supplyAsync(() -> {
            try {
                StringBuilder sb = new StringBuilder();
                sb.append("Generate ").append(lang).append(" code for the following task.");
                if (codeStyle != null) sb.append(" Style: ").append(codeStyle).append('.');
                if (includeTests) sb.append(" Include unit tests.");
                sb.append("\n\nTask: ").append(taskDescription).append("\n\n");
                if (fileName != null) sb.append("Target file: ").append(fileName).append("\n\n");
                if (existingCode != null && !existingCode.trim().isEmpty()) {
                    sb.append("Existing context:\n\n").append(existingCode).append("\n\n");
                }
                sb.append("Return only code when appropriate.");

                return askQuestion(sb.toString(), existingCode, fileName).get();
            } catch (Exception e) {
                LOG.error("Failed to generate code (extended)", e);
                return "// Error occurred during code generation";
            }
        });
    }
    
    /**
     * Sync with Jira tasks
     */
    public java.util.concurrent.CompletableFuture<java.util.List<java.util.Map<String, Object>>> syncJiraTasks() {
        // No Jira backend in this repo; return empty list to populate UI safely
        return java.util.concurrent.CompletableFuture.completedFuture(java.util.Collections.emptyList());
    }

    /**
     * Detect interview mode (stubbed: returns false). Could be extended to query local services.
     */
    public CompletableFuture<Boolean> detectInterviewMode() {
        return CompletableFuture.completedFuture(false);
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
