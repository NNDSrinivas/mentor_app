package com.aimentor.intellij.ui;

import com.aimentor.intellij.services.AIMentorService;
import com.intellij.icons.AllIcons;
import com.intellij.openapi.project.Project;
import com.intellij.openapi.ui.Messages;
import com.intellij.ui.components.*;
import com.intellij.ui.table.JBTable;
import com.intellij.util.ui.FormBuilder;
import com.intellij.util.ui.JBUI;

import javax.swing.*;
import javax.swing.table.DefaultTableModel;
import java.awt.*;
import java.awt.event.ActionEvent;
import java.awt.event.ActionListener;
import java.util.Map;

/**
 * Main AI Mentor tool window panel
 */
public class AIMentorToolWindow {
    private final Project project;
    private final AIMentorService service;
    private JPanel mainPanel;
    private JBTextArea chatArea;
    private JBTextField questionField;
    private JBButton askButton;
    private JBTable tasksTable;
    private DefaultTableModel tasksTableModel;
    private JBLabel statusLabel;
    private JBButton syncJiraButton;
    private JBButton detectInterviewButton;
    
    public AIMentorToolWindow(Project project, AIMentorService service) {
        this.project = project;
        this.service = service;
        initComponents();
    }
    
    private void initComponents() {
        // Chat section
        chatArea = new JBTextArea(15, 50);
        chatArea.setEditable(false);
        chatArea.setLineWrap(true);
        chatArea.setWrapStyleWord(true);
        chatArea.setText("Welcome to AI Mentor!\nAsk questions about your code, get suggestions, or request code generation.\n\n");
        
        questionField = new JBTextField();
        questionField.setPlaceholderText("Ask AI Mentor a question...");
        
        askButton = new JBButton("Ask", AllIcons.Actions.Execute);
        askButton.addActionListener(new AskQuestionListener());
        
        // Enter key support for question field
        questionField.addActionListener(e -> askButton.doClick());
        
        // Tasks section
        String[] columnNames = {"Task", "Status", "Priority", "Assignee"};
        tasksTableModel = new DefaultTableModel(columnNames, 0) {
            @Override
            public boolean isCellEditable(int row, int column) {
                return false;
            }
        };
        tasksTable = new JBTable(tasksTableModel);
        tasksTable.setRowHeight(25);
        
        // Control buttons
        syncJiraButton = new JBButton("Sync Jira Tasks", AllIcons.Actions.Refresh);
        syncJiraButton.addActionListener(new SyncJiraListener());
        
        detectInterviewButton = new JBButton("Check Interview Mode", AllIcons.General.Balloon);
        detectInterviewButton.addActionListener(new DetectInterviewListener());
        
        // Status label
        statusLabel = new JBLabel("Ready");
        statusLabel.setForeground(JBUI.CurrentTheme.Label.foreground());
        
        // Layout
        JPanel chatPanel = createChatPanel();
        JPanel tasksPanel = createTasksPanel();
        JPanel controlPanel = createControlPanel();
        
        mainPanel = new JPanel(new BorderLayout());
        
        JTabbedPane tabbedPane = new JTabbedPane();
        tabbedPane.addTab("Chat", AllIcons.General.Balloon, chatPanel);
        tabbedPane.addTab("Tasks", AllIcons.General.TodoDefault, tasksPanel);
        
        mainPanel.add(tabbedPane, BorderLayout.CENTER);
        mainPanel.add(controlPanel, BorderLayout.SOUTH);
        
        // Load initial data
        loadJiraTasks();
        checkInterviewMode();
    }
    
    private JPanel createChatPanel() {
        JPanel questionPanel = new JPanel(new BorderLayout());
        questionPanel.add(questionField, BorderLayout.CENTER);
        questionPanel.add(askButton, BorderLayout.EAST);
        
        return FormBuilder.createFormBuilder()
            .addComponent(new JBScrollPane(chatArea))
            .addVerticalGap(5)
            .addComponent(questionPanel)
            .getPanel();
    }
    
    private JPanel createTasksPanel() {
        JPanel buttonPanel = new JPanel(new FlowLayout(FlowLayout.LEFT));
        buttonPanel.add(syncJiraButton);
        
        return FormBuilder.createFormBuilder()
            .addComponent(buttonPanel)
            .addComponent(new JBScrollPane(tasksTable))
            .getPanel();
    }
    
    private JPanel createControlPanel() {
        JPanel panel = new JPanel(new BorderLayout());
        panel.setBorder(JBUI.Borders.empty(5));
        
        JPanel leftPanel = new JPanel(new FlowLayout(FlowLayout.LEFT));
        leftPanel.add(statusLabel);
        
        JPanel rightPanel = new JPanel(new FlowLayout(FlowLayout.RIGHT));
        rightPanel.add(detectInterviewButton);
        
        panel.add(leftPanel, BorderLayout.WEST);
        panel.add(rightPanel, BorderLayout.EAST);
        
        return panel;
    }
    
    private class AskQuestionListener implements ActionListener {
        @Override
        public void actionPerformed(ActionEvent e) {
            String question = questionField.getText().trim();
            if (question.isEmpty()) return;
            
            // Add question to chat
            appendToChat("You: " + question + "\n");
            questionField.setText("");
            askButton.setEnabled(false);
            statusLabel.setText("Processing...");
            
            // Get response from AI
            service.askQuestion(question, null, null)
                .thenAccept(response -> {
                    SwingUtilities.invokeLater(() -> {
                        appendToChat("AI Mentor: " + response + "\n\n");
                        askButton.setEnabled(true);
                        statusLabel.setText("Ready");
                    });
                })
                .exceptionally(throwable -> {
                    SwingUtilities.invokeLater(() -> {
                        appendToChat("Error: " + throwable.getMessage() + "\n\n");
                        askButton.setEnabled(true);
                        statusLabel.setText("Error");
                    });
                    return null;
                });
        }
    }
    
    private class SyncJiraListener implements ActionListener {
        @Override
        public void actionPerformed(ActionEvent e) {
            syncJiraButton.setEnabled(false);
            statusLabel.setText("Syncing Jira tasks...");
            
            service.syncJiraTasks()
                .thenAccept(tasks -> {
                    SwingUtilities.invokeLater(() -> {
                        updateTasksTable(tasks);
                        syncJiraButton.setEnabled(true);
                        statusLabel.setText("Jira sync completed");
                    });
                })
                .exceptionally(throwable -> {
                    SwingUtilities.invokeLater(() -> {
                        Messages.showErrorDialog(
                            project,
                            "Failed to sync Jira tasks: " + throwable.getMessage(),
                            "Jira Sync Error"
                        );
                        syncJiraButton.setEnabled(true);
                        statusLabel.setText("Jira sync failed");
                    });
                    return null;
                });
        }
    }
    
    private class DetectInterviewListener implements ActionListener {
        @Override
        public void actionPerformed(ActionEvent e) {
            checkInterviewMode();
        }
    }
    
    private void appendToChat(String text) {
        SwingUtilities.invokeLater(() -> {
            chatArea.append(text);
            chatArea.setCaretPosition(chatArea.getDocument().getLength());
        });
    }
    
    private void loadJiraTasks() {
        service.syncJiraTasks()
            .thenAccept(this::updateTasksTable)
            .exceptionally(throwable -> {
                // Silently fail initial load
                return null;
            });
    }
    
    private void updateTasksTable(java.util.List<Map<String, Object>> tasks) {
        tasksTableModel.setRowCount(0);
        for (Map<String, Object> task : tasks) {
            tasksTableModel.addRow(new Object[]{
                task.get("summary"),
                task.get("status"),
                task.get("priority"),
                task.get("assignee")
            });
        }
    }
    
    private void checkInterviewMode() {
        service.detectInterviewMode()
            .thenAccept(isInterview -> {
                SwingUtilities.invokeLater(() -> {
                    if (isInterview) {
                        statusLabel.setText("Interview mode detected!");
                        statusLabel.setForeground(Color.ORANGE);
                        appendToChat("🎯 Interview mode detected! I'm ready to help with coding questions.\n\n");
                    } else {
                        statusLabel.setText("Ready");
                        statusLabel.setForeground(JBUI.CurrentTheme.Label.foreground());
                    }
                });
            })
            .exceptionally(throwable -> {
                // Silently handle errors
                return null;
            });
    }
    
    public JPanel getPanel() {
        return mainPanel;
    }
}
