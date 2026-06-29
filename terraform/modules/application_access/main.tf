terraform {
  required_version = ">= 1.2"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">= 5.0"
    }
  }
}

variable "username" {
  description = "Name of the IAM user to attach policies to"
  type        = string
}

resource "aws_iam_user" "this" {
  name = var.username

  lifecycle {
    ignore_changes = [tags, tags_all]
  }
}

variable "buckets" {
  description = "Bucket names and policy descriptions"
  type = object({
    files        = object({ name = string, description = optional(string) })
    public_files = object({ name = string, description = optional(string) })
    logs         = object({ name = string, description = optional(string) })
  })
}

data "aws_iam_policy_document" "files" {
  statement {
    sid = "VisualEditor0"
    actions = [
      "s3:PutObject",
      "s3:GetObjectAttributes",
      "s3:GetObject",
      "s3:GetObjectVersion",
      "s3:GetObjectVersionAttributes",
      "s3:DeleteObject",
      "s3:DeleteObjectVersion",
    ]
    resources = ["arn:aws:s3:::${var.buckets.files.name}/*"]
  }
}

data "aws_iam_policy_document" "public_files" {
  statement {
    sid = "VisualEditor0"
    actions = [
      "s3:PutObject",
      "s3:GetObjectAttributes",
      "s3:GetObject",
      "s3:GetObjectVersion",
      "s3:GetObjectVersionAttributes",
      "s3:DeleteObject",
      "s3:DeleteObjectVersion",
    ]
    resources = ["arn:aws:s3:::${var.buckets.public_files.name}/*"]
  }
}

data "aws_iam_policy_document" "logs" {
  statement {
    sid = "AllowWriteLogs"
    actions = [
      "s3:PutObject",
    ]
    resources = ["arn:aws:s3:::${var.buckets.logs.name}/*"]
  }
}

resource "aws_iam_policy" "files" {
  name        = var.buckets.files.name
  description = var.buckets.files.description
  policy      = data.aws_iam_policy_document.files.json
}

resource "aws_iam_policy" "public_files" {
  name        = var.buckets.public_files.name
  description = var.buckets.public_files.description
  policy      = data.aws_iam_policy_document.public_files.json
}

resource "aws_iam_policy" "logs" {
  name        = var.buckets.logs.name
  description = var.buckets.logs.description
  policy      = data.aws_iam_policy_document.logs.json
}

resource "aws_iam_user_policy_attachment" "files" {
  user       = aws_iam_user.this.name
  policy_arn = aws_iam_policy.files.arn
}

resource "aws_iam_user_policy_attachment" "public_files" {
  user       = aws_iam_user.this.name
  policy_arn = aws_iam_policy.public_files.arn
}

resource "aws_iam_user_policy_attachment" "logs" {
  user       = aws_iam_user.this.name
  policy_arn = aws_iam_policy.logs.arn
}
