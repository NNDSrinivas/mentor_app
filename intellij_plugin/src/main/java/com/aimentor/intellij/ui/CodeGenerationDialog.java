package com.aimentor.intellij.ui;

import com.intellij.openapi.project.Project;
import com.intellij.openapi.ui.DialogWrapper;
import com.intellij.openapi.ui.ValidationInfo;
import com.intellij.ui.components.JBCheckBox;
import com.intellij.ui.components.JBLabel;
import com.intellij.ui.components.JBScrollPane;
import com.intellij.ui.components.JBTextArea;
import com.intellij.ui.components.JBTextField;
import com.intellij.util.ui.FormBuilder;
import org.jetbrains.annotations.NotNull;
import org.jetbrains.annotations.Nullable;

import javax.swing.*;
import java.awt.*;
import java.util.Arrays;
import java.util.List;

/**
 * Dialog for configuring code generation parameters
 */
public class CodeGenerationDialog extends DialogWrapper {
    private JBTextArea taskDescriptionArea;
    private JComboBox<String> codeStyleCombo;
    private JBCheckBox includeTestsCheckBox;
    private JBCheckBox replaceSelectionCheckBox;
    private JBTextArea existingCodeArea;
    private final String fileName;
    private final String fileType;
    private final String existingCode;
    
    private static final List<String> CODE_STYLES = Arrays.asList(
        "Clean and readable",
        "Performance optimized",
        "Enterprise patterns",
        "Functional programming",
        "Object-oriented",
        "Minimal and concise"
    );
    
    public CodeGenerationDialog(@Nullable Project project, String fileName, String fileType, String existingCode) {
        super(project);
        this.fileName = fileName;
        this.fileType = fileType;
        this.existingCode = existingCode;
        
        setTitle("Generate Code with AI Mentor");
        setSize(600, 500);
        init();
    }
    
    @Override
    protected @Nullable JComponent createCenterPanel() {
        // Task description
        taskDescriptionArea = new JBTextArea(5, 40);
        taskDescriptionArea.setLineWrap(true);
        taskDescriptionArea.setWrapStyleWord(true);
        taskDescriptionArea.setPlaceholderText("Describe what code you want to generate (e.g., 'Create a function to sort users by name', 'Add error handling to this method')");
        
        // Code style selection
        codeStyleCombo = new JComboBox<>(CODE_STYLES.toArray(new String[0]));
        codeStyleCombo.setSelectedIndex(0);
        
        // Options
        includeTestsCheckBox = new JBCheckBox("Generate unit tests", false);
        replaceSelectionCheckBox = new JBCheckBox("Insert/replace code in editor", true);
        
        // Existing code context (read-only)
        existingCodeArea = new JBTextArea(8, 40);
        existingCodeArea.setEditable(false);
        existingCodeArea.setBackground(UIManager.getColor("Panel.background"));
        if (existingCode != null && !existingCode.trim().isEmpty()) {
            existingCodeArea.setText(existingCode.length() > 1000 ? 
                existingCode.substring(0, 1000) + "..." : existingCode);
        } else {
            existingCodeArea.setText("No existing code context");
        }
        
        FormBuilder builder = FormBuilder.createFormBuilder()
            .addLabeledComponent(new JBLabel("Task Description*:"), new JBScrollPane(taskDescriptionArea))
            .addVerticalGap(10)
            .addLabeledComponent(new JBLabel("Code Style:"), codeStyleCombo)
            .addVerticalGap(10)
            .addComponent(includeTestsCheckBox)
            .addComponent(replaceSelectionCheckBox)
            .addVerticalGap(15)
            .addLabeledComponent(new JBLabel("Existing Code Context:"), new JBScrollPane(existingCodeArea));
        
        if (fileName != null) {
            builder.addVerticalGap(5)
                   .addComponent(new JBLabel("File: " + fileName + " (" + fileType + ")"));
        }
        
        return builder.getPanel();
    }
    
    @Override
    protected ValidationInfo doValidate() {
        String taskDescription = getTaskDescription();
        if (taskDescription == null || taskDescription.trim().isEmpty()) {
            return new ValidationInfo("Please provide a task description", taskDescriptionArea);
        }
        if (taskDescription.trim().length() < 10) {
            return new ValidationInfo("Task description should be more detailed", taskDescriptionArea);
        }
        return null;
    }
    
    public String getTaskDescription() {
        return taskDescriptionArea.getText();
    }
    
    public String getCodeStyle() {
        return (String) codeStyleCombo.getSelectedItem();
    }
    
    public boolean shouldIncludeTests() {
        return includeTestsCheckBox.isSelected();
    }
    
    public boolean shouldReplaceSelection() {
        return replaceSelectionCheckBox.isSelected();
    }
}
