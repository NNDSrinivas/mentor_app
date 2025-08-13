#!/bin/bash

# Script to resolve merge conflicts in all feature branches
set -e

echo "🚀 Starting systematic merge conflict resolution..."

# Get list of all remote feature branches (excluding main)
branches=$(git branch -r | grep -v 'origin/main' | grep -v 'HEAD' | sed 's/origin\///' | tr -d ' ')

success_count=0
conflict_count=0
total_count=0

for branch in $branches; do
    echo ""
    echo "📋 Processing branch: $branch"
    total_count=$((total_count + 1))
    
    # Switch to main first
    git checkout main -q
    
    # Check out the feature branch
    if git checkout $branch -q 2>/dev/null; then
        echo "✅ Checked out $branch"
    else
        echo "❌ Failed to checkout $branch, skipping..."
        continue
    fi
    
    # Try to merge main
    if git merge main --no-edit 2>/dev/null; then
        echo "✅ $branch: Clean merge (fast-forward)"
        
        # Push the updated branch
        if git push origin $branch 2>/dev/null; then
            echo "✅ $branch: Pushed successfully"
            success_count=$((success_count + 1))
        else
            echo "⚠️ $branch: Failed to push"
        fi
    else
        echo "🔧 $branch: Merge conflicts detected"
        conflict_count=$((conflict_count + 1))
        
        # Check what files have conflicts
        conflicted_files=$(git status --porcelain | grep "^UU\|^AA\|^DD" | cut -c4- || true)
        
        if [ -n "$conflicted_files" ]; then
            echo "💥 Conflicted files in $branch:"
            echo "$conflicted_files"
            echo ""
            echo "⚠️ Manual resolution needed for $branch"
            echo "   Run: git checkout $branch && git merge main"
            echo "   Then resolve conflicts and commit"
        fi
        
        # Abort the merge to clean up
        git merge --abort 2>/dev/null || true
    fi
done

echo ""
echo "📊 Summary:"
echo "   Total branches: $total_count"
echo "   ✅ Successfully merged: $success_count"
echo "   🔧 Need manual resolution: $conflict_count"

# Switch back to main
git checkout main -q
echo ""
echo "🎉 Conflict resolution analysis complete!"
